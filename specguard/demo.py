"""Opt-in, read-only presentation of a verified historical audit."""

import json
from hashlib import sha256
from html import escape
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from .core import CONTRADICTIONS, provider_evidence, verify_evidence
from .ingest import ingest_document
from .models import AuditResult, Evidence, Finding, SourceDocument, SourceLocation

MAX_ARTIFACT_BYTES = 2 * 1024 * 1024
SEVERITY = {
    "critical": "Критический",
    "major": "Существенный",
    "minor": "Незначительный",
    "informational": "Информационный",
}
STATUS = {
    "confirmed": "Подтверждено",
    "requires_clarification": "Требуется уточнение",
    "context_dependent": "Зависит от контекста",
}
VERDICT = {
    "ready": "Готово",
    "ready_with_conditions": "Готово при выполнении условий",
    "requires_revision": "Требуется доработка",
    "unable_to_determine": "Готовность не определена",
}
HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Robots-Tag": "noindex, nofollow",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
    ),
}
STYLE = """
    * { box-sizing: border-box; }
    body { margin: 0; background: #f7f6fc; color: #111322; font: 16px/1.5 system-ui, sans-serif; }
    main { width: min(100% - 32px, 1040px); margin: 32px auto; overflow-wrap: anywhere; }
    header, article { padding: 20px; background: white; border: 1px solid #e6e1f0; border-radius: 14px; }
    header, article { margin-bottom: 12px; }
    h1, h2, h3 { margin: 0 0 .5em; line-height: 1.2; }
    nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
    a { color: #5521ca; }
    a:focus-visible { outline: 2px solid #7828ee; outline-offset: 3px; }
    :target { outline: 3px solid #7828ee; scroll-margin: 16px; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; font: .9rem/1.5 ui-monospace, monospace; }
    blockquote { margin-left: 0; padding: 4px 12px; border-left: 3px solid #7828ee; }
    .meta { color: #4a4760; overflow-wrap: anywhere; }
    .download { display: inline-block; padding: 8px 12px; background: #5521ca; color: white; border-radius: 8px; }
"""


def _read(path: Path) -> bytes:
    with path.open("rb") as source:
        data = source.read(MAX_ARTIFACT_BYTES + 1)
    if not data or len(data) > MAX_ARTIFACT_BYTES:
        raise ValueError("invalid archive file size")
    return data


def _load(directory: Path) -> tuple[AuditResult, SourceDocument, bytes]:
    audit = AuditResult.model_validate_json(_read(directory / "audit.json"))
    source = ingest_document("requirements.md", _read(directory / "requirements.md"))
    report = _read(directory / "report.md")
    manifest = json.loads(_read(directory / "verification.json"))
    if (
        audit.mode != "live"
        or not audit.coverage.complete
        or len(audit.documents) != 1
        or audit.documents[0].document_id != source.document_id
        or audit.documents[0].sha256 != source.sha256
        or manifest["audit_id"] != audit.audit_id
        or manifest["source_sha256"] != source.sha256
        or manifest["report_sha256"] != sha256(report).hexdigest()
    ):
        raise ValueError("archive integrity check failed")

    blocks = {(source.document_id, block.block_id): block for block in source.blocks}
    references = [entry for item in audit.requirements for entry in item.evidence] + [
        entry for item in audit.findings for entry in (*item.evidence, *item.counterevidence)
    ]
    if len(references) != manifest["evidence_records_checked"] or any(
        verify_evidence(provider_evidence(entry), blocks, allowed_scopes=True) != entry
        for entry in references
    ):
        raise ValueError("archive evidence check failed")
    return audit, source, report


def _lines(location: SourceLocation) -> str:
    if location.line_start is None:
        return "строки не указаны"
    if location.line_end is None or location.line_end == location.line_start:
        return f"строка {location.line_start}"
    return f"строки {location.line_start}–{location.line_end}"


def _citations(evidence: list[Evidence]) -> str:
    items = []
    for entry in evidence:
        location = entry.location
        text = (
            f"<blockquote>{escape(entry.quote)}</blockquote>"
            if entry.quote is not None
            else f"<p>Зона поиска отсутствующих сведений · {escape(entry.scope or '')}</p>"
        )
        items.append(f'<li><a href="#source-{escape(location.block_id)}">{_lines(location)}</a>{text}</li>')
    return "<ul>" + "".join(items) + "</ul>"


def _finding(finding: Finding, requirements: dict[str, str]) -> str:
    links = ", ".join(
        f'<a href="#requirement-{escape(item)}">{escape(requirements[item])}</a>'
        for item in finding.requirement_ids
        if item in requirements
    )
    linked_requirements = f"<p>Связанные требования · {links}</p>" if links else ""
    counter = (
        f"<h4>Контрдоказательства</h4>{_citations(finding.counterevidence)}"
        if finding.counterevidence
        else ""
    )
    return f"""
    <article id="finding-{escape(finding.finding_id)}">
      <h3>{escape(finding.title)}</h3>
      <p class="meta">{SEVERITY[finding.severity]} · {STATUS[finding.status]}</p>
      <p>{escape(finding.explanation)}</p>
      <p><strong>Влияние</strong> · {escape(finding.impact)}</p>
      <p><strong>Рекомендация</strong> · {escape(finding.recommendation)}</p>
      {linked_requirements}
      <h4>Доказательства</h4>{_citations(finding.evidence)}
      {counter}
    </article>"""


def _render(audit: AuditResult, source: SourceDocument) -> str:
    names = {item.requirement_id: item.original_id or item.requirement_id for item in audit.requirements}
    requirements = "".join(
        f'<article id="requirement-{escape(item.requirement_id)}">'
        f"<h3>{escape(names[item.requirement_id])}</h3><p>{escape(item.summary)}</p>"
        f"{_citations(item.evidence)}</article>"
        for item in audit.requirements
    )
    findings = "".join(_finding(item, names) for item in audit.findings)
    contradictions = "".join(
        f'<li><a href="#finding-{escape(item.finding_id)}">{escape(item.title)}</a> '
        f"· {STATUS[item.status]}</li>"
        for item in audit.findings
        if item.kind in CONTRADICTIONS
    )
    sources = "".join(
        f'<article id="source-{escape(block.block_id)}">'
        f"<h3>{escape(block.section or 'Первоисточник')} · {_lines(block.location)}</h3>"
        f"<pre>{escape(block.text)}</pre></article>"
        for block in source.blocks
    )
    date = audit.created_at.date().isoformat()
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Архивный аудит · SpecGuard AI</title>
<style>{STYLE}</style>
</head>
<body><main>
<header>
  <a href="/">SpecGuard AI</a>
  <h1>Архивный аудит официального ТЗ</h1>
  <p>Завершённая проверка DeepSeek от {date}. Здесь представлен сохранённый результат.</p>
  <p class="meta">Модель · {escape(audit.model)} · Аудит · {escape(audit.audit_id)}</p>
  <p><strong>{VERDICT[audit.readiness.verdict]}</strong> · {escape(audit.readiness.rationale)}</p>
  <p><a class="download" href="/demo/report.md">Скачать оригинальный отчёт Markdown</a></p>
  <nav aria-label="Разделы архивного аудита">
    <a href="#requirements">Требования ({len(audit.requirements)})</a>
    <a href="#findings">Замечания ({len(audit.findings)})</a>
    <a href="#contradictions">Противоречия</a>
    <a href="#sources">Первоисточник</a>
  </nav>
</header>
<section id="requirements"><h2>Требования</h2>{requirements}</section>
<section id="contradictions"><h2>Противоречия</h2>
  {"<ul>" + contradictions + "</ul>" if contradictions else "<p>Противоречия отсутствуют.</p>"}
</section>
<section id="findings"><h2>Замечания</h2>{findings}</section>
<section id="sources"><h2>Первоисточник</h2>{sources}</section>
</main></body></html>
"""


def demo_router(directory: str | Path | None) -> APIRouter:
    """Serve the official archive only when its directory is explicitly configured."""
    router = APIRouter(prefix="/demo", include_in_schema=False)
    if not directory:
        return router
    try:
        audit, source, report = _load(Path(directory))
    except (OSError, KeyError, TypeError, ValueError):
        raise RuntimeError("Configured SpecGuard demo archive is missing or invalid.") from None
    page = _render(audit, source).encode("utf-8")

    @router.get("", response_class=HTMLResponse)
    @router.get("/", response_class=HTMLResponse)
    def archive() -> HTMLResponse:
        return HTMLResponse(page, headers=HEADERS)

    @router.get("/report.md")
    def download() -> Response:
        return Response(
            report,
            media_type="text/markdown",
            headers={**HEADERS, "Content-Disposition": 'attachment; filename="specguard-official-report.md"'},
        )

    return router
