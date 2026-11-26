"""Session-scoped local REST API. Start one Uvicorn worker."""

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from .http_models import (
    Attachment,
    AuditRequest,
    AuditStatus,
    ComparisonRequest,
    ComparisonResult,
    CopilotRequest,
    CopilotResponse,
    ErrorResponse,
    Purpose,
    RevisionDraft,
    RevisionRequest,
    SessionTicket,
)
from .models import AuditResult, DocumentMetadata, Finding, Requirement, SourceBlock


@asynccontextmanager
async def lifespan(app):
    from .service import sessions

    async def cleanup():
        while True:
            await asyncio.sleep(60)
            sessions.purge()

    cleaner = asyncio.create_task(cleanup())
    try:
        yield
    finally:
        cleaner.cancel()
        await asyncio.gather(cleaner, return_exceptions=True)


app = FastAPI(
    lifespan=lifespan,
    title="SpecGuard AI",
    version="0.1.0",
    responses={n: {"model": ErrorResponse} for n in (400, 401, 404, 409, 413, 422, 429, 503)},
)
bearer = HTTPBearer(auto_error=False)
UPLOAD_LIMIT = 5 * 1024 * 1024


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    return JSONResponse(status_code=422, content={"detail": "Некорректные параметры запроса."})


@app.exception_handler(StarletteHTTPException)
async def http_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


def session(auth: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    from .service import sessions

    return sessions.authenticate(auth.credentials if auth else "")


Session = Annotated[object, Depends(session)]
AuditPath = "/audits/{audit_id}"
UploadBody = {
    "requestBody": {
        "required": True,
        "content": {
            t: {"schema": {"type": "string", "format": "binary"}}
            for t in ("application/pdf", "text/markdown", "text/plain", "application/octet-stream")
        },
    }
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sessions", status_code=201, response_model=SessionTicket)
def create_session():
    from .service import sessions

    return sessions.create()


@app.post("/documents", status_code=201, response_model=DocumentMetadata, openapi_extra=UploadBody)
async def upload(request: Request, s: Session, filename: str = Query(min_length=1, max_length=200)):
    from .service import save_document

    return await run_in_threadpool(save_document, s, filename, await request.body())


@app.post("/audits", status_code=202, response_model=AuditStatus)
def start_audit(req: AuditRequest, tasks: BackgroundTasks, s: Session):
    from .service import queue_audit

    return queue_audit(s, req, tasks)


@app.get(AuditPath, response_model=AuditStatus)
def status(audit_id: str, s: Session):
    from .service import job_status

    return job_status(s, audit_id)


@app.get(AuditPath + "/result", response_model=AuditResult)
def result(audit_id: str, s: Session):
    from .service import get_result

    return get_result(s, audit_id)


@app.get(AuditPath + "/requirements/{requirement_id}", response_model=Requirement)
def requirement(audit_id: str, requirement_id: str, s: Session):
    return lookup(result(audit_id, s).requirements, "requirement_id", requirement_id)


@app.get(AuditPath + "/findings/{finding_id}", response_model=Finding)
def finding(audit_id: str, finding_id: str, s: Session):
    return lookup(result(audit_id, s).findings, "finding_id", finding_id)


def lookup(items, field, value):
    for item in items:
        if getattr(item, field) == value:
            return item
    raise HTTPException(404, "Запись не найдена.")


@app.get(AuditPath + "/sources/{document_id}/{block_id}", response_model=SourceBlock)
def source(audit_id: str, document_id: str, block_id: str, s: Session):
    from .service import audit_document

    return lookup(audit_document(s, audit_id, document_id).blocks, "block_id", block_id)


@app.get(AuditPath + "/report", response_class=Response, responses={200: {"content": {"text/markdown": {}}}})
def report(audit_id: str, s: Session):
    from .report import render_markdown

    return Response(
        render_markdown(result(audit_id, s)),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="report.md"'},
    )


@app.post(AuditPath + "/attachments", status_code=201, response_model=Attachment, openapi_extra=UploadBody)
async def add_attachment(
    request: Request,
    audit_id: str,
    s: Session,
    purpose: Purpose,
    filename: str = Query(min_length=1, max_length=200),
):
    from .service import save_attachment

    return await run_in_threadpool(save_attachment, s, audit_id, filename, await request.body(), purpose)


@app.get(AuditPath + "/attachments", response_model=list[Attachment])
def list_attachments(audit_id: str, s: Session):
    from .service import attachments

    return attachments(s, audit_id)


@app.delete(AuditPath + "/attachments/{attachment_id}", status_code=204)
def remove_attachment(audit_id: str, attachment_id: str, s: Session) -> Response:
    from .service import drop_attachment

    drop_attachment(s, audit_id, attachment_id)
    return Response(status_code=204)


@app.post(AuditPath + "/copilot", response_model=CopilotResponse)
def copilot(audit_id: str, req: CopilotRequest, s: Session):
    from .copilot import ask

    return ask(s, audit_id, req)


@app.post(AuditPath + "/revisions", response_model=RevisionDraft)
def revision(audit_id: str, req: RevisionRequest, s: Session):
    from .copilot import propose

    return propose(s, audit_id, req)


@app.post(AuditPath + "/comparisons", response_model=ComparisonResult)
def compare(audit_id: str, req: ComparisonRequest, s: Session):
    from .copilot import compare_documents

    return compare_documents(s, audit_id, req)


class BodyLimit:
    """Bound actual bytes before JSON or document parsing, including chunked requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        path = scope["path"]
        root = scope.get("root_path", "")
        if root and path.startswith(f"{root}/"):
            path = path[len(root) :]
        limit = UPLOAD_LIMIT if path == "/documents" or path.endswith("/attachments") else 32768
        data = bytearray()
        while True:
            part = await receive()
            if part["type"] == "http.disconnect":
                return
            chunk = part.get("body", b"")
            if len(data) + len(chunk) > limit:
                return await JSONResponse({"detail": "Превышен размер запроса."}, status_code=413)(
                    scope, receive, send
                )
            data.extend(chunk)
            if not part.get("more_body"):
                break

        delivered = False

        async def replay():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(data), "more_body": False}

        await self.app(scope, replay, send)


app.add_middleware(BodyLimit)
