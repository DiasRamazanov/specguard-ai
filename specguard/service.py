"""Single-process, bounded, ephemeral storage for the local demo API."""

import os
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from .http_models import Attachment, AuditStatus, Event, SessionTicket
from .ingest import DocumentError, ingest_document
from .models import AuditResult, DocumentMetadata, SourceDocument

TTL = 3600
lock = threading.RLock()
audit_slots = threading.BoundedSemaphore(2)
parse_slots = threading.BoundedSemaphore(2)


@dataclass
class Job:
    id: str
    docs: list[SourceDocument]
    status: str = "queued"
    result: AuditResult | None = None
    error: str | None = None
    events: list[Event] = field(default_factory=list)
    attachments: dict[str, tuple[Attachment, SourceDocument]] = field(default_factory=dict)
    history: list[tuple[tuple[str, ...], dict[str, str]]] = field(default_factory=list)
    conversation_lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class SessionData:
    expires: float
    documents: dict[str, SourceDocument] = field(default_factory=dict)
    jobs: dict[str, Job] = field(default_factory=dict)


class Sessions:
    def __init__(self):
        self.data = {}

    def purge(self):
        with lock:
            now = time.monotonic()
            for key in [k for k, v in self.data.items() if v.expires <= now]:
                del self.data[key]

    def create(self):
        with lock:
            self.purge()
            if len(self.data) >= 24:
                raise HTTPException(429, "Достигнут лимит сессий.")
            token = secrets.token_urlsafe(32)
            self.data[token] = SessionData(time.monotonic() + TTL)
            return SessionTicket(token=token, ttl_seconds=TTL)

    def authenticate(self, token):
        with lock:
            self.purge()
            if token not in self.data:
                raise HTTPException(401, "Требуется действующая сессия.")
            return self.data[token]


sessions = Sessions()


def metadata(document):
    return DocumentMetadata.model_validate(document.model_dump(include=set(DocumentMetadata.model_fields)))


@contextmanager
def capacity(semaphore):
    if not semaphore.acquire(blocking=False):
        raise HTTPException(429, "Сервис занят. Повторите попытку позже.")
    try:
        yield
    finally:
        semaphore.release()


def parse(filename, data):
    with capacity(parse_slots):
        try:
            return ingest_document(filename, data)
        except DocumentError as exc:
            raise HTTPException(422, str(exc)) from None


def save_document(s, filename, data):
    doc = parse(filename, data)
    with lock:
        if doc.document_id not in s.documents and len(s.documents) >= 6:
            raise HTTPException(429, "Достигнут лимит документов сессии.")
        s.documents.setdefault(doc.document_id, doc)
        return metadata(s.documents[doc.document_id])


def job_for(s, audit_id):
    with lock:
        if audit_id not in s.jobs:
            raise HTTPException(404, "Аудит не найден.")
        return s.jobs[audit_id]


def event(job, stage, details=None):
    with lock:
        # Result data retains all findings; polling keeps a bounded recent window.
        sequence = job.events[-1].sequence + 1 if job.events else 1
        item = Event(
            sequence=sequence,
            stage=stage,
            time=datetime.now(timezone.utc),
            finding_id=next(iter((details or {}).get("finding_ids", [])), None),
        )
        job.events.append(item)
        del job.events[:-256]


def job_status(s, audit_id):
    with lock:
        job = job_for(s, audit_id)
        return AuditStatus(audit_id=job.id, status=job.status, events=list(job.events), error=job.error)


def provider_for(mode, consent):
    if mode == "offline":
        return None
    if not consent:
        raise HTTPException(400, "Для отправки текста в DeepSeek требуется явное согласие.")
    if os.getenv("SPECGUARD_LIVE") != "1" or not os.getenv("DEEPSEEK_API_KEY"):
        raise HTTPException(503, "Сервер не настроен для внешнего анализа.")
    from .intelligence import Intelligence, IntelligenceError

    try:
        return Intelligence(live=True)
    except IntelligenceError as exc:
        raise HTTPException(503, f"Ошибка провайдера ({exc.code}).") from None


def queue_audit(s, req, tasks):
    if len(set(req.document_ids)) != len(req.document_ids):
        raise HTTPException(422, "Документ указан несколько раз.")
    with lock:
        if any(i not in s.documents for i in req.document_ids):
            raise HTTPException(404, "Документ не найден.")
        if len(s.jobs) >= 6:
            raise HTTPException(429, "Достигнут лимит аудитов сессии.")
        provider = provider_for(req.mode, req.allow_external_processing)
        if not audit_slots.acquire(blocking=False):
            raise HTTPException(429, "Очередь аудита занята.")
        job = Job(uuid4().hex, [s.documents[key] for key in req.document_ids])
        s.jobs[job.id] = job
        event(job, "document_received")
        tasks.add_task(run_job, job, provider)
        return job_status(s, job.id)


def run_job(job, provider):
    try:
        from .core import audit_documents
        from .report import render_markdown

        with lock:
            job.status = "running"

        def progress(stage, details=None):
            if stage not in {"document_received", "generating_report", "completed", "failed"}:
                event(job, stage, details)

        result = audit_documents(job.docs, provider=provider, audit_id=job.id, progress=progress)
        event(job, "generating_report")
        render_markdown(result)
        with lock:
            job.result = result
            job.status = "completed"
            event(job, "completed")
    except Exception:
        with lock:
            job.status = "failed"
            job.error = "Не удалось завершить технический прогон."
            event(job, "failed")
    finally:
        audit_slots.release()


def get_result(s, audit_id):
    with lock:
        job = job_for(s, audit_id)
        if job.result is None:
            raise HTTPException(409, job.error or "Результат ещё не готов.")
        return job.result


def audit_document(s, audit_id, document_id):
    with lock:
        job = job_for(s, audit_id)
        for doc in [*job.docs, *(d for _, d in job.attachments.values())]:
            if doc.document_id == document_id:
                return doc
    raise HTTPException(404, "Источник не найден.")


def save_attachment(s, audit_id, filename, data, purpose):
    job = job_for(s, audit_id)
    get_result(s, audit_id)
    event(job, "attachment_received")
    event(job, "attachment_reading")
    doc = parse(filename, data)
    with lock:
        if len(job.attachments) >= 4:
            raise HTTPException(429, "Достигнут лимит вложений.")
        attachment = Attachment(attachment_id=uuid4().hex, document=metadata(doc), purpose=purpose)
        job.attachments[attachment.attachment_id] = attachment, doc
        return attachment


def attachments(s, audit_id):
    with lock:
        return [meta for meta, _ in job_for(s, audit_id).attachments.values()]


def drop_attachment(s, audit_id, attachment_id):
    job = job_for(s, audit_id)
    with capacity(job.conversation_lock), lock:
        if job.attachments.pop(attachment_id, None) is None:
            raise HTTPException(404, "Вложение не найдено.")
        job.history.clear()
