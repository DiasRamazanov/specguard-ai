from hashlib import sha256

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from specguard.core import audit_documents
from specguard.demo import demo_router
from specguard.ingest import ingest_document
from specguard.report import render_json, render_markdown


@pytest.fixture
def archived_audit(tmp_path):
    source = "# Ограничения\n\n- REQ-42: GET /cats должен возвращать 404 OK.\n"
    document = ingest_document("requirements.md", source.encode())
    audit = audit_documents([document])
    assert audit.findings
    finding = audit.findings[0].model_copy(update={"kind": "contradiction", "title": "<em>Замечание</em>"})
    audit = audit.model_copy(
        update={"mode": "live", "coverage": audit.coverage.model_copy(update={"complete": True})}
    )
    audit.findings[0] = finding
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(render_json(audit), encoding="utf-8")
    report = render_markdown(audit).encode()
    (tmp_path / "report.md").write_bytes(report)
    (tmp_path / "requirements.md").write_bytes(source.encode())
    references = sum(len(item.evidence) for item in audit.requirements) + sum(
        len(item.evidence) + len(item.counterevidence) for item in audit.findings
    )
    (tmp_path / "verification.json").write_text(
        f'{{"audit_id":"{audit.audit_id}","source_sha256":"{document.sha256}",'
        f'"report_sha256":"{sha256(report).hexdigest()}","evidence_records_checked":{references}}}'
    )
    return audit, report


def test_demo_requires_configuration():
    app = FastAPI()
    app.include_router(demo_router(None))
    with TestClient(app) as client:
        assert client.get("/demo/").status_code == 404
        assert client.get("/demo/report.md").status_code == 404


def test_demo_displays_archive_and_downloads_original_report(tmp_path, archived_audit):
    audit, report = archived_audit
    app = FastAPI()
    app.include_router(demo_router(tmp_path))
    with TestClient(app) as client:
        page = client.get("/demo/")
        assert client.get("/demo").content == page.content
        assert page.status_code == 200
        assert "Архивный аудит" in page.text
        assert "Завершённая проверка DeepSeek" in page.text
        assert "REQ-42" in page.text
        assert f'href="#finding-{audit.findings[0].finding_id}"' in page.text
        assert f'href="#source-{audit.findings[0].evidence[0].location.block_id}"' in page.text
        assert "&lt;em&gt;Замечание&lt;/em&gt;" in page.text
        assert "<em>Замечание</em>" not in page.text
        assert page.headers["cache-control"] == "no-store"
        assert "default-src 'none'" in page.headers["content-security-policy"]

        response = client.get("/demo/report.md")
        assert response.status_code == 200
        assert response.content == report
        assert response.headers["content-type"].startswith("text/markdown")
        assert response.headers["content-disposition"].startswith("attachment;")
        assert client.post("/demo/").status_code == 405
        assert client.get("/demo/audit.json").status_code == 404


def test_demo_rejects_changed_report(tmp_path, archived_audit):
    (tmp_path / "report.md").write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="Configured SpecGuard demo archive is missing or invalid"):
        demo_router(tmp_path)
