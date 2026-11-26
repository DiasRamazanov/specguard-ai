"""Exercise the deployed entry point using synthetic uploads."""

import pytest
from fastapi.testclient import TestClient

from specguard.cloud import create_app


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "index.html").write_text("<main>Workspace</main>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "bundle.js").write_text("/* compiled module */", encoding="utf-8")
    # Only compiled assets and the app entry point are public.
    (tmp_path / "dev").mkdir()
    (tmp_path / "dev" / "spec-states.html").write_text("dev harness", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist, monkeypatch):
    monkeypatch.setenv("SPECGUARD_LIVE", "0")
    monkeypatch.delenv("SPECGUARD_DEMO_DIR", raising=False)
    from specguard.service import sessions

    monkeypatch.setattr(sessions, "data", {})
    with TestClient(create_app(dist)) as client:
        yield client


def test_cloud_serves_workspace_and_compiled_assets(client):
    assert client.get("/health").json() == client.get("/api/health").json() == {"status": "ok"}
    root = client.get("/")
    assert root.text == "<main>Workspace</main>"
    assert root.headers["X-Content-Type-Options"] == "nosniff"
    assert client.get("/workspace/audit", headers={"Accept": "text/html"}).text == root.text
    assert client.get("/assets/bundle.js").text == "/* compiled module */"
    for path in (
        "/assets/missing.js",
        "/dev/spec-states.html",
        "/src/dev/SpecStates.tsx",
        "/demo/",
        "/api/missing",
    ):
        assert client.get(path, headers={"Accept": "text/html"}).status_code == 404


def test_cloud_provider_disabled_even_when_key_is_present(dist, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "synthetic-key")
    monkeypatch.setenv("SPECGUARD_LIVE", "1")
    with pytest.raises(RuntimeError, match="requires SPECGUARD_LIVE=0"), TestClient(create_app(dist)):
        pass


def test_cloud_upload_poll_report_and_session_ownership(client):
    initial = client.post("/api/sessions")
    assert initial.headers["Cache-Control"] == "no-store"
    headers = {"Authorization": "Bearer " + initial.json()["token"]}
    upload_path = "/api/documents?filename=sample.md"
    # Exceed the JSON limit while remaining below the document limit.
    body = "# Требования\n\n- REQ-1: Система хранит журнал операций TBD дней.\n".encode() + b" " * 33000
    response = client.post(upload_path, headers=headers, content=body)
    assert response.status_code == 201, response.text
    req = {"document_ids": [response.json()["document_id"]]}
    live = client.post(
        "/api/audits", headers=headers, json={**req, "mode": "live", "allow_external_processing": True}
    )
    assert live.status_code == 503
    queued = client.post("/api/audits", headers=headers, json=req)
    assert queued.status_code == 202
    assert queued.json()["status"] == "queued"
    path = "/api/audits/" + queued.json()["audit_id"]
    status = client.get(path, headers=headers).json()
    assert status["status"] == "completed"
    assert status["events"][-1]["stage"] == "completed"
    report = client.get(path + "/report", headers=headers)
    assert report.status_code == 200 and "Паспорт" in report.text
    other_token = client.post("/api/sessions").json()["token"]
    assert client.get(path + "/report", headers={"Authorization": "Bearer " + other_token}).status_code == 404
    assert client.post(upload_path, headers=headers, content=b"x" * (5 * 1024 * 1024 + 1)).status_code == 413
    assert client.post("/api/audits", headers=headers, content=b"x" * 32769).status_code == 413


def test_public_writes_are_rate_limited_without_blocking_health(client):
    for _ in range(60):
        assert client.post("/api/documents?filename=sample.md", content=b"").status_code == 401
    response = client.post("/api/documents?filename=sample.md", content=b"")
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"
    assert client.get("/health").status_code == 200


def test_cloud_recovers_after_audit_worker_failure(client, monkeypatch):
    from specguard import core

    audit = core.audit_documents

    def fail_once(*args, **kwargs):
        monkeypatch.setattr(core, "audit_documents", audit)
        raise RuntimeError("private source")

    monkeypatch.setattr(core, "audit_documents", fail_once)
    token = client.post("/api/sessions").json()["token"]
    headers = {"Authorization": "Bearer " + token}
    uploaded = client.post("/api/documents?filename=recovery.md", headers=headers, content=b"# Rules")
    req = {"document_ids": [uploaded.json()["document_id"]]}
    first = client.post("/api/audits", headers=headers, json=req)
    failed_path = "/api/audits/" + first.json()["audit_id"]
    status = client.get(failed_path, headers=headers)
    assert status.json()["status"] == "failed"
    assert "private source" not in status.text
    assert client.get(failed_path + "/report", headers=headers).status_code == 409
    retry = client.post("/api/audits", headers=headers, json=req)
    assert retry.status_code == 202
    retry_status = client.get("/api/audits/" + retry.json()["audit_id"], headers=headers)
    assert retry_status.json()["status"] == "completed"
