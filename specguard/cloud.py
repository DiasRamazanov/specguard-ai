"""Single-worker public ASGI entry point for the compiled workspace and offline API."""

import logging
import os
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath
from time import monotonic

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from .api import app as api
from .api import health
from .api import lifespan as api_lifespan
from .demo import demo_router

logger = logging.getLogger(__name__)
WRITE_METHODS = {"POST", "DELETE", "PUT", "PATCH"}
RESERVED_SPA_PATHS = {"api", "assets", "demo", "dev", "src"}


class PublicLimits:
    """Bound anonymous traffic, including bodies buffered ahead of upload parsing."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self.windows: dict[str, deque[float]] = {key: deque() for key in ("session", "write", "read")}
        self.active_writes = 0

    def permit(self, kind: str, capacity: int) -> bool:
        now = monotonic()
        window = self.windows[kind]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= capacity:
            return False
        window.append(now)
        return True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        mutates = scope["method"] in WRITE_METHODS
        is_api = path.startswith("/api/") and (mutates or path != "/api/health")
        write = is_api and mutates
        started = False

        async def redact(response):
            nonlocal started
            if response["type"] == "http.response.start":
                started = True
                headers = MutableHeaders(scope=response)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("Referrer-Policy", "no-referrer")
                if is_api:
                    headers.setdefault("Cache-Control", "no-store")
            await send(response)

        if write:
            kind, limit = ("session", 24) if path.rstrip("/") == "/api/sessions" else ("write", 60)
            allowed = self.active_writes < 8 and self.permit(kind, limit)
        else:
            allowed = not is_api or self.permit("read", 1200)
        if not allowed:
            response = JSONResponse(
                {"detail": "Слишком много запросов. Повторите попытку позже."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, redact)
            return

        if write:
            self.active_writes += 1
        try:
            await self.app(scope, receive, redact)
        except Exception:
            logger.error("Unhandled public request failure")
            if not started:
                response = JSONResponse({"detail": "Внутренняя ошибка сервера."}, status_code=500)
                await response(scope, receive, redact)
        finally:
            if write:
                self.active_writes -= 1


def create_app(frontend_dir: str | Path | None = None) -> FastAPI:
    dist = Path(frontend_dir or os.environ.get("SPECGUARD_FRONTEND_DIR", "frontend/dist")).resolve()

    @asynccontextmanager
    async def lifespan(_app):
        if os.environ.get("SPECGUARD_LIVE") == "1":
            raise RuntimeError("The public cloud entry point requires SPECGUARD_LIVE=0.")
        if not (dist / "index.html").is_file() or not (dist / "assets").is_dir():
            raise RuntimeError("Compile the frontend before starting the cloud entry point.")
        async with api_lifespan(api):
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(PublicLimits)
    app.add_api_route("/health", health)
    app.mount("/api", api)
    app.include_router(demo_router(os.environ.get("SPECGUARD_DEMO_DIR")))
    app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False))

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def workspace(path: str, request: Request):
        segments = path.split("/")
        if (
            segments[0] in RESERVED_SPA_PATHS
            or PurePosixPath(path).suffix
            or (path and "text/html" not in request.headers.get("accept", ""))
        ):
            raise HTTPException(404)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
