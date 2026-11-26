"""Exercise compact recovery via the public role entry point and a local fake transport."""

import json
from copy import deepcopy

import pytest

from specguard.intelligence import Intelligence, IntelligenceError, verify

TEXT = "Правило А: “выплата” — через 5 дней.\n"
EXCERPT = "“выплата” — через 5 дней."
SRC = {"document_id": "main", "block_id": "same", "section": "Условия"}
OTHER = {**SRC, "document_id": "other"}
BLOCKS = [
    {**SRC, "text": TEXT},
    {**OTHER, "text": "При отмене срок составляет 7 дней."},
]
CITE = {"document_id": "main", "block_id": "same", "quote": EXCERPT}
REQ = {"requirement_id": "req-original-AAA", "original_id": "FR-17", "evidence": [CITE]}
CAND = {
    "kind": "ambiguity",
    "title": "Даты",
    "description": "Разные сроки.",
    "severity": "minor",
    "status": "requires_clarification",
    "requirement_ids": [REQ["requirement_id"]],
    "evidence": [CITE],
    "impact": "Неясно, когда ожидать выплату.",
    "recommendation": "Уточнить сроки.",
    "uncertainty": "Возможно исключение.",
}
CRITIC = {**CAND, "candidate_id": "candidate-original-AAA"}
FINDING = {**CAND, "finding_id": "finding-original-AAA"}
CONTEXT = {"blocks": BLOCKS, "requirements": [REQ]}
VERDICT = {
    "candidate_id": "C1",
    "verdict": "rejected",
    "evidence": [],
    "counterevidence": ["E2"],
    "severity": "minor",
    "explanation": "Исключение меняет срок.",
    "uncertainty": "Умеренная.",
    "action": "Проверить исключение.",
}
ASSESS = {
    "requirement_id": "R1",
    "criteria": {"completeness": ["requires_clarification", "Срок уточняется."]},
    "findings": [],
    "uncertainty": "Умеренная.",
}
RISK = {
    "finding_id": "F1",
    "impact": "Можно выбрать неверный срок.",
    "stakeholders": ["Банк"],
    "priority": "Уточнить до реализации.",
    "evidence": ["E3"],
    "uncertainty": "Умеренная.",
}


@pytest.fixture
def transport(monkeypatch, tmp_path):
    monkeypatch.setenv("SPECGUARD_LIVE", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "injected-fixture")
    monkeypatch.setenv("SPECGUARD_BUDGET_DB", str(tmp_path / "ledger.sqlite"))
    monkeypatch.setenv("SPECGUARD_RETRIES", "0")
    monkeypatch.setenv("DEEPSEEK_REASONING_MODEL", "mock-reasoner")

    def run(role, payload, reply, *, references=True, error=None):
        engine = Intelligence(live=True, reference_roles=references)
        requests = []

        def request(path, body=None):
            if path == "/models":
                return {"data": [{"id": "mock-reasoner"}]}
            assert path == "/chat/completions"
            requests.append(body)
            if isinstance(reply, Exception):
                raise reply
            return {
                "model": "mock-reasoner",
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(reply)}}],
                "usage": {"prompt_tokens": 200, "completion_tokens": 64, "total_tokens": 264},
            }

        monkeypatch.setattr(engine.provider, "_request", request)
        if error:
            with pytest.raises(IntelligenceError, match=f"^{error}$"):
                engine.run(role, payload)
            output = None
        else:
            output = engine.run(role, payload)
            assert verify(role, payload, output) == output
        assert len(requests) == len(engine.records) == 1
        record = engine.records[0]
        assert record["status"] == (error or "validated")
        assert record["prompt_version"] == ("v1-refs1" if references and role != "global" else "v1")
        body = requests[0]
        assert body["reasoning_effort"] == engine.provider.reasoning_effort
        assert body["response_format"] == {"type": "json_object"}
        return output, json.loads(body["messages"][1]["content"]), record

    return run


def test_critic_grounded_rejection_and_cross_document_counterevidence(transport):
    payload = {**CONTEXT, "candidates": [CRITIC]}
    out, sent, _ = transport("critic", payload, {"verdicts": [VERDICT]})
    row = out["verdicts"][0]
    assert row["candidate_id"] == CRITIC["candidate_id"] and row["verdict"] == "rejected"
    assert row["evidence"] == [] and row["counterevidence"] == [
        {
            "document_id": "other",
            "block_id": "same",
            "kind": "quote",
            "quote": BLOCKS[1]["text"],
            "scope": None,
        }
    ]
    assert sent["candidates"][0]["support_refs"] == ["E3"]
    assert sent["blocks"][0]["excerpts"] == {"E3": EXCERPT}
    assert sent["requirements"][0]["requirement_id"] == "R1"

    verdict = {**VERDICT, "verdict": "confirmed", "evidence": ["E3"], "counterevidence": []}
    out, _, _ = transport("critic", payload, {"verdicts": [verdict]})
    assert out["verdicts"][0]["evidence"][0]["quote"] == EXCERPT


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"evidence": ["E2"]}, "unrelated_evidence_reference"),
        ({"candidate_id": "candidate-original-AAA"}, "unknown_role_reference"),
        ({"counterevidence": ["E999"]}, "unknown_role_reference"),
        ({"evidence": [{**CITE, "quote": "подмена"}]}, "invalid_role_output"),
        ({"evidence": "E3"}, "invalid_role_output"),
        ({"verdict": "confirmed", "evidence": []}, "missing_support"),
        ({"severity": "medium"}, "invalid_role_output"),
        ({"verdict": "duplicate", "duplicate_of": "C1"}, "invalid_duplicate"),
        ({"bogus": 0}, "invalid_role_output"),
    ],
)
def test_critic_rejects_unverifiable_responses(transport, change, error):
    transport(
        "critic", {**CONTEXT, "candidates": [CRITIC]}, {"verdicts": [{**VERDICT, **change}]}, error=error
    )


def test_critic_requires_every_verdict_and_keeps_duplicate_order(transport):
    payload = {**CONTEXT, "candidates": [CRITIC, {**CRITIC, "candidate_id": "candidate-original-BBB"}]}
    transport("critic", payload, {"verdicts": [VERDICT]}, error="incomplete_verdicts")
    reviews = [
        {**VERDICT, "verdict": "requires_clarification"},
        {**VERDICT, "candidate_id": "C2", "verdict": "duplicate", "duplicate_of": "C1"},
    ]
    out, _, _ = transport("critic", payload, {"verdicts": reviews})
    assert out["verdicts"][1]["duplicate_of"] == CRITIC["candidate_id"]


def test_individual_retains_all_criteria_and_scopes_real_absence(transport):
    payload = {**CONTEXT, "criteria": ["completeness"]}
    finding = {**CAND, "requirement_ids": ["R1"], "evidence": ["E3", "E4"]}
    out, sent, _ = transport("individual", payload, {"assessments": [{**ASSESS, "findings": [finding]}]})
    row = out["assessments"][0]
    assert sent["requirements"][0]["absence_refs"] == ["E4"]
    assert row["requirement_id"] == REQ["requirement_id"]
    assert row["criteria"][0] == {
        "criterion": "completeness",
        "status": "requires_clarification",
        "explanation": "Срок уточняется.",
    }
    assert row["findings"][0]["evidence"][1] == {
        "document_id": "main",
        "block_id": "same",
        "kind": "absence",
        "quote": None,
        "scope": "same",
    }
    transport(
        "individual", payload, {"assessments": [{**ASSESS, "criteria": {}}]}, error="incomplete_criteria"
    )
    transport("individual", payload, {"assessments": []}, error="incomplete_assessment")
    transport(
        "individual",
        payload,
        {"assessments": [{**ASSESS, "requirement_id": "FR-17"}]},
        error="unknown_role_reference",
    )


def test_risk_accepts_only_evidence_belonging_to_its_target(transport):
    payload = {**CONTEXT, "findings": [FINDING]}
    out, _, _ = transport("risk", payload, {"risks": [RISK]})
    risk = out["risks"][0]
    assert risk["finding_id"] == FINDING["finding_id"] and risk["evidence"][0]["quote"] == EXCERPT
    transport(
        "risk", payload, {"risks": [{**RISK, "evidence": ["E2"]}]}, error="unrelated_evidence_reference"
    )
    transport("risk", payload, {"risks": []}, error="incomplete_risks")


def test_compact_mode_preserves_default_and_other_roles(transport):
    payload = {**CONTEXT, "candidates": [CRITIC]}
    normal = {**VERDICT, "candidate_id": CRITIC["candidate_id"], "counterevidence": [CITE]}
    _, sent, _ = transport("critic", payload, {"verdicts": [normal]}, references=False)
    assert sent["candidates"][0]["evidence"][0]["quote"] == EXCERPT
    _, sent, _ = transport("global", CONTEXT, {"findings": []})
    assert sent["requirements"][0]["requirement_id"] == REQ["requirement_id"]


def test_failed_transport_retains_unknown_usage(transport):
    _, _, record = transport(
        "critic",
        {**CONTEXT, "candidates": [CRITIC]},
        IntelligenceError("provider_timeout", retryable=True),
        error="provider_timeout",
    )
    assert record["input_tokens"] is None and record["output_tokens"] is None


def test_long_passage_can_supply_exact_counterevidence(transport):
    payload = deepcopy({**CONTEXT, "candidates": [CRITIC]})
    payload["blocks"][1]["text"] = "А" * 12000 + "Конец."
    out, _, _ = transport("critic", payload, {"verdicts": [{**VERDICT, "counterevidence": ["E3"]}]})
    assert out["verdicts"][0]["counterevidence"][0]["quote"] == "Конец."


def test_critic_cannot_confirm_from_an_absence_alone(transport):
    absence = {
        "document_id": "main",
        "block_id": "same",
        "kind": "absence",
        "scope": "Условия",
        "quote": None,
    }
    payload = {**CONTEXT, "candidates": [{**CRITIC, "evidence": [absence]}]}
    verdict = {**VERDICT, "verdict": "confirmed", "evidence": ["E4"]}
    transport("critic", payload, {"verdicts": [verdict]}, error="missing_support")
