"""Exercise session ownership and the frontend's public HTTP flow without external calls."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from specguard.api import app
from specguard.http_models import AuditStatus
from specguard.intelligence import verify
from specguard.service import sessions

BODY = "- SG-501: Система должна хранить журнал операций в течение TBD дней.".encode()
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def api(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("SPECGUARD_LIVE", raising=False)
    sessions.data.clear()
    with TestClient(app) as client:
        yield client


def ticket(api):
    response = api.post("/sessions")
    assert response.status_code == 201
    return {"Authorization": "Bearer " + response.json()["token"]}


def upload(api, headers, data=BODY, filename="input.md"):
    response = api.post("/documents", headers=headers, params={"filename": filename}, content=data)
    assert response.status_code == 201, response.text
    return response.json()["document_id"]


@pytest.fixture
def audited(api):
    h = ticket(api)
    doc_id = upload(api, h)
    res = api.post("/audits", headers=h, json={"document_ids": [doc_id]})
    assert res.status_code == 202
    base = "/audits/" + res.json()["audit_id"]
    status = api.get(base, headers=h).json()
    assert status["status"] == "completed", status
    return h, doc_id, base


def test_schemas_match_runtime():
    assert app.openapi() == json.loads((ROOT / "contracts/openapi.json").read_text())
    mock = json.loads((ROOT / "contracts/fixtures/mock-progress.json").read_text())
    assert mock["fixture"] == "mock"
    AuditStatus.model_validate(mock["status"])


def test_capability_is_required(api):
    assert api.get("/health").json() == {"status": "ok"}
    assert api.post("/documents?filename=x.md", content=BODY).status_code == 401
    h = ticket(api)
    assert api.post("/documents?filename=x.pdf", content=b"bad", headers=h).status_code == 422
    assert api.post("/audits", headers=h, content=b"x" * 32769).status_code == 413
    assert (
        api.post("/documents?filename=x.md", headers=h, content=b"x" * (5 * 1024 * 1024 + 1)).status_code
        == 413
    )


def test_audit_and_drilldown(api, audited):
    h, doc_id, base = audited
    audit = api.get(base + "/result", headers=h).json()
    assert not audit["coverage"]["complete"]
    assert audit["readiness"]["verdict"] == "unable_to_determine"
    req, finding = audit["requirements"][0], audit["findings"][0]
    for key, record in [("requirements", req), ("findings", finding)]:
        ident = record.get("requirement_id") or record["finding_id"]
        assert api.get(f"{base}/{key}/{ident}", headers=h).json() == record
    ref = finding["evidence"][0]
    block = api.get(f"{base}/sources/{doc_id}/" + ref["location"]["block_id"], headers=h).json()
    assert ref["quote"] in block["text"]
    assert "Паспорт" in api.get(base + "/report", headers=h).text
    stages = [x["stage"] for x in api.get(base, headers=h).json()["events"]]
    assert stages[0] == "document_received" and stages[-1] == "completed"
    assert "generating_report" in stages
    assert stages.count("completed") == 1


def test_attachments_ownership_and_removal(api, audited):
    h, doc_id, base = audited
    before = api.get(base + "/result", headers=h).json()
    attach = api.post(
        base + "/attachments?filename=extra.md&purpose=context",
        headers=h,
        content="# Справка\n\nАрхив содержит квитанции.".encode(),
    ).json()
    aid = attach["attachment_id"]
    request = {"question": "квитанции", "attachment_ids": [aid]}
    reply = api.post(base + "/copilot", headers=h, json=request)
    assert reply.status_code == 200, reply.text
    evidence = reply.json()["evidence"][0]
    assert evidence["location"]["document_id"] == attach["document"]["document_id"]
    outsider = ticket(api)
    assert api.post("/audits", headers=outsider, json={"document_ids": [doc_id]}).status_code == 404
    for url in [base, base + "/attachments", base + "/result", base + "/report"]:
        assert api.get(url, headers=outsider).status_code == 404
    assert api.delete(base + "/attachments/" + aid, headers=outsider).status_code == 404
    assert api.delete(base + "/attachments/" + aid, headers=h).status_code == 204
    assert api.post(base + "/copilot", headers=h, json=request).status_code == 404
    assert not api.get(base + "/attachments", headers=h).json()
    assert api.get(base + "/result", headers=h).json() == before


def test_live_requires_server_and_caller_consent(api, audited):
    h, doc_id, base = audited
    for url, body in [("/audits", {"document_ids": [doc_id]}), (base + "/copilot", {"question": "Поясни"})]:
        assert api.post(url, headers=h, json=dict(body, mode="live")).status_code == 400
        assert (
            api.post(url, headers=h, json=dict(body, mode="live", allow_external_processing=True)).status_code
            == 503
        )


def test_session_expires(api):
    h = ticket(api)
    sessions.data[h["Authorization"].split()[1]].expires = 0
    assert api.get("/audits/private", headers=h).status_code == 401


def test_mocked_context_revision_and_comparison(api, audited, monkeypatch):
    h, doc_id, base = audited
    before = api.get(base + "/result", headers=h).json()
    req, finding = before["requirements"][0], before["findings"][0]
    attachment = api.post(
        base + "/attachments?filename=other.md&purpose=comparison",
        headers=h,
        content="- AB-1: Архив должен хранить квитанции три дня.".encode(),
    ).json()

    class MockSemantic:
        def run(self, role, payload):
            ref = payload["requirements"][0]["evidence"][0]
            if role == "copilot":
                output = dict(
                    answer="Срок хранения требует уточнения.",
                    evidence=[ref],
                    related_finding_ids=[finding["finding_id"]],
                    questions=[],
                    actions=["open_evidence"],
                    uncertainty="Не указан срок.",
                    followups=[],
                    insufficient_evidence=False,
                )
            elif role == "revision":
                output = dict(
                    original_text=ref["quote"],
                    revision=None,
                    alternatives=[],
                    explanation="Необходим срок.",
                    evidence=[ref],
                    assumptions=[],
                    decisions=["Укажите срок хранения."],
                    acceptance_tests=[],
                    requires_human_approval=True,
                )
            else:
                other = payload["blocks"][-1]
                output = dict(
                    relationship="uncertain",
                    changes=[
                        dict(
                            kind="added",
                            alignment="uncertain",
                            description="Возможное дополнение.",
                            evidence=[
                                dict(
                                    document_id=other["document_id"],
                                    block_id=other["block_id"],
                                    quote=other["text"],
                                )
                            ],
                            requirement_ids=[],
                            related_finding_ids=[],
                            uncertainty="Требует подтверждения.",
                        )
                    ],
                    questions=[],
                )
            return verify(role, payload, output)

    monkeypatch.setattr("specguard.copilot.provider_for", lambda mode, consent: MockSemantic())
    reply = api.post(
        base + "/copilot",
        headers=h,
        json={
            "question": "Поясните замечание.",
            "mode": "live",
            "allow_external_processing": True,
            "finding_id": finding["finding_id"],
        },
    )
    assert reply.status_code == 200, reply.text
    draft = api.post(
        base + "/revisions",
        headers=h,
        json={
            "requirement_id": req["requirement_id"],
            "finding_id": finding["finding_id"],
            "allow_external_processing": True,
        },
    )
    assert draft.status_code == 200, draft.text
    assert draft.json()["requires_human_approval"] is True
    comparison = api.post(
        base + "/comparisons",
        headers=h,
        json={
            "primary_document_id": doc_id,
            "attachment_ids": [attachment["attachment_id"]],
            "purpose": "Сравнить сроки.",
            "allow_external_processing": True,
        },
    )
    assert comparison.status_code == 200, comparison.text
    assert (
        comparison.json()["changes"][0]["evidence"][0]["location"]["document_id"]
        == attachment["document"]["document_id"]
    )
    assert api.get(base + "/result", headers=h).json() == before


@pytest.mark.parametrize("flag", ["on", "true", 1])
@pytest.mark.parametrize(
    "model,payload",
    [
        ("AuditRequest", {"document_ids": ["d"]}),
        ("CopilotRequest", {"question": "Почему?"}),
        ("RevisionRequest", {"requirement_id": "r", "finding_id": "f"}),
        ("ComparisonRequest", {"primary_document_id": "d", "attachment_ids": ["a"], "purpose": "Сравнить"}),
    ],
)
def test_external_consent_requires_json_boolean(model, payload, flag):
    from pydantic import ValidationError

    from specguard import http_models

    with pytest.raises(ValidationError):
        getattr(http_models, model).model_validate({**payload, "allow_external_processing": flag})
