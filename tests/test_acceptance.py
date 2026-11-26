"""Offline acceptance checks through the public parser, audit, report, and CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from specguard.ingest import DocumentError, ingest_document

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pdf_source():
    with pymupdf.open() as pdf:
        first = pdf.new_page()
        first.insert_text((72, 72), "Routing")
        first.insert_text((72, 110), "REQ-701: The service must log routing decisions.")
        second = pdf.new_page()
        second.insert_text((72, 72), "REQ-702: The service must log delivery failures.")
        pdf.set_toc([[1, "Routing", 1]])
        return pdf.tobytes()


def test_markdown_preserves_nested_sections_tables_and_exact_offsets():
    raw = (
        "# Документы\r\n"
        "## Маршрутизация\r\n"
        "\r\n"
        "| ID | Требование |\r\n"
        "| --- | --- |\r\n"
        "| REQ-170 | Система должна сохранять время маршрутизации. |\r\n"
    )
    document = ingest_document(r"C:\upload\routing.markdown", raw.encode())

    assert document.filename == "routing.markdown"
    assert document.original_text == raw
    table_header, row = document.blocks[-2:]
    assert table_header.kind == "table_header"
    assert table_header.location.line_start == 4
    assert row.kind == "table_row"
    assert row.section == "Документы › Маршрутизация"
    assert row.location.line_start == row.location.line_end == 6
    assert raw[row.location.char_start : row.location.char_end] == row.text
    assert row.text == "| REQ-170 | Система должна сохранять время маршрутизации. |"


def test_pdf_preserves_page_coordinates_and_exact_offsets(pdf_source):
    document = ingest_document("routing.pdf", pdf_source)

    assert document.page_count == 2
    assert not document.warnings
    assert document.blocks[0].kind == "heading"
    assert document.blocks[0].location.section == "Routing"
    assert {block.location.page for block in document.blocks} == {1, 2}
    block = next(block for block in document.blocks if "REQ-702" in block.text)
    location = block.location
    assert location.page == 2 and location.bbox
    assert document.original_text[location.char_start : location.char_end] == block.text


@pytest.mark.parametrize(
    ("filename", "data"),
    [
        ("unsupported.csv", b"id,text\n1,test"),
        ("fake.pdf", b"# disguised plaintext"),
        ("broken.pdf", b"%PDF-1.7\nthis has no PDF objects"),
        ("invalid.md", b"\x00\x93\xff"),
        ("empty.md", b""),
        ("blank.md", b"  \r\n   "),
    ],
)
def test_unusable_uploads_return_document_errors(filename, data):
    with pytest.raises(DocumentError):
        ingest_document(filename, data)


def test_pdf_discloses_blank_pages_and_rejects_a_document_without_text():
    with pymupdf.open() as pdf:
        pdf.new_page()
        with pytest.raises(DocumentError):
            ingest_document("no-text.pdf", pdf.tobytes())
        page = pdf.new_page()
        page.insert_text((72, 72), "The service must preserve receipt timestamps.")
        document = ingest_document("partial.pdf", pdf.tobytes())
    assert document.page_count == 2
    assert any("1:" in warning and "текстового слоя" in warning for warning in document.warnings)


def test_stable_ids_omit_headings_examples_and_metadata():
    from specguard.core import audit_documents

    text = """# Импорт файлов

Этот документ описывает импорт.

- REQ-901: Система должна отклонять файлы объёмом более 8 МБ.
- Система должна регистрировать время завершения импорта.

```text
REQ-000: Система должна пропускать проверку в образце.
```
"""
    first_doc = ingest_document("import.md", text.encode())
    second_doc = ingest_document("copy.md", text.encode())
    first = audit_documents([first_doc])
    second = audit_documents([second_doc])

    assert first_doc.document_id == second_doc.document_id
    assert [row.original_id for row in first.requirements] == ["REQ-901", None]
    assert [row.requirement_id for row in first.requirements] == [
        row.requirement_id for row in second.requirements
    ]
    assert len({row.requirement_id for row in first.requirements}) == 2
    for row in first.requirements:
        quote = row.evidence[0]
        block = next(block for block in first_doc.blocks if block.block_id == quote.location.block_id)
        assert quote.quote and quote.quote in block.text
        assert quote.location.line_start in {5, 6}


def test_offline_finding_and_report_expose_evidence_and_incomplete_analysis():
    from specguard.core import audit_documents
    from specguard.report import render_markdown

    document = ingest_document(
        "receipts.md",
        ("# Выписки\n\n- REQ-971: Система должна применять настройки согласно REQ-970.\n").encode(),
    )
    result = audit_documents([document])
    finding = next(row for row in result.findings if row.kind == "undefined_reference")

    assert len({row.finding_id for row in result.findings}) == len(result.findings)
    assert finding.document_ids == [document.document_id]
    assert finding.requirement_ids == [result.requirements[0].requirement_id]
    assert any(item.kind == "absence" and item.scope and not item.quote for item in finding.evidence)
    assert not result.coverage.complete
    assert result.readiness.verdict == "unable_to_determine"
    assert result.mode == "offline"
    report = render_markdown(result)
    for needle in (
        "Паспорт",
        "Реестр требований",
        "Сводка",
        "Итог",
        "REQ-971",
        "receipts.md",
    ):
        assert needle in report


def run_cli(*args):
    environment = os.environ.copy()
    environment.pop("DEEPSEEK_API_KEY", None)
    environment.pop("SPECGUARD_LIVE", None)
    return subprocess.run(
        [sys.executable, "-m", "specguard", "validate", *map(str, args)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_cli_validates_pdf_and_writes_structured_output(tmp_path, pdf_source):
    source = tmp_path / "routing.pdf"
    source.write_bytes(pdf_source)
    target = tmp_path / "audit.json"

    invocation = run_cli("--input", source, "--output", target, "--offline")

    assert invocation.returncode == 0, invocation.stderr
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["documents"][0]["page_count"] == 2
    assert data["mode"] == "offline"
    assert data["requirements"][-1]["original_id"] == "REQ-702"
    assert data["requirements"][-1]["evidence"][0]["location"]["page"] == 2


def test_cli_rejects_malformed_pdf_without_leaving_report(tmp_path):
    source = tmp_path / "broken.pdf"
    source.write_bytes(b"plaintext")
    target = tmp_path / "report.md"

    invocation = run_cli("--input", source, "--output", target, "--offline")

    assert invocation.returncode != 0
    assert "PDF" in invocation.stderr
    assert not target.exists()


def test_cli_writes_russian_markdown_for_a_document_with_defects(tmp_path):
    source = tmp_path / "retention.md"
    source.write_text(
        "# Хранение выписок\n\n"
        "- REQ-975: Система должна сохранять время формирования выписки.\n"
        "- REQ-975: Система должна удалять устаревшие выписки.\n",
        encoding="utf-8",
    )
    target = tmp_path / "report.md"

    invocation = run_cli("--input", source, "--output", target, "--offline")

    assert invocation.returncode == 0, invocation.stderr
    markdown = target.read_text(encoding="utf-8")
    assert "Реестр требований" in markdown
    assert "REQ-975" in markdown
    assert "дубли" in markdown.lower() or "повтор" in markdown.lower()


class ScriptedProvider:
    """Reply at the engine boundary using independently checked role contracts."""

    def __init__(self, fail_role=None):
        self.fail_role = fail_role
        self.roles = []
        self.records = []

    def run(self, role, payload):
        from specguard.intelligence import CRITERIA, verify
        from specguard.provider import IntelligenceError

        self.roles.append(role)
        if role == self.fail_role:
            raise IntelligenceError("provider_timeout")

        if role == "extract":
            output = {
                "requirements": [],
                "unclassified": [
                    {key: block[key] for key in ("document_id", "block_id")} for block in payload["blocks"]
                ],
            }
        elif role == "individual":
            output = {
                "assessments": [
                    {
                        "requirement_id": requirement["requirement_id"],
                        "uncertainty": "Не установлена.",
                        "criteria": [
                            {"criterion": name, "status": "valid", "explanation": "Проверено."}
                            for name in payload.get("criteria", CRITERIA)
                        ],
                        "findings": [],
                    }
                    for requirement in payload["requirements"]
                ],
            }
        elif role == "global":
            requirement = payload["requirements"][0]
            finding = {
                "kind": "atomicity",
                "title": "Два отдельных действия",
                "description": "Требование объединяет регистрацию и уведомление.",
                "severity": "major",
                "status": "confirmed",
                "criterion": "singularity",
                "requirement_ids": [requirement["requirement_id"]],
                "evidence": requirement["evidence"],
                "impact": "Нельзя независимо проверить два действия.",
                "recommendation": "Разделить формулировку на два требования.",
                "uncertainty": "Не установлена.",
            }
            output = {"findings": [finding, finding]}
        elif role == "critic":
            output = {
                "verdicts": [
                    {
                        "candidate_id": candidate["candidate_id"],
                        "verdict": "confirmed",
                        "evidence": candidate["evidence"],
                        "counterevidence": [],
                        "severity": candidate["severity"],
                        "explanation": "Ссылка подтверждает наличие двух действий.",
                        "uncertainty": "Не установлена.",
                        "action": "Уточнить отдельные действия.",
                    }
                    for candidate in payload["candidates"]
                ]
            }
        elif role == "risk":
            output = {
                "risks": [
                    {
                        "finding_id": finding["finding_id"],
                        "impact": finding["impact"],
                        "stakeholders": ["Команда тестирования"],
                        "priority": "Доработать перед тестированием.",
                        "evidence": finding["evidence"],
                        "uncertainty": "Не установлена.",
                    }
                    for finding in payload["findings"]
                ]
            }
        else:
            pytest.fail(f"Unexpected provider role: {role}")
        return verify(role, payload, output)


@pytest.mark.parametrize("fail_role", [None, "global"])
def test_engine_keeps_analysis_coverage_honest_on_provider_failure(fail_role):
    from specguard.core import audit_documents

    document = ingest_document(
        "actions.md",
        (
            "# Действия\n\n- REQ-981: Система должна регистрировать событие и отправлять уведомление.\n"
        ).encode(),
    )
    provider = ScriptedProvider(fail_role=fail_role)

    result = audit_documents([document], provider=provider)

    assert result.mode == "live"
    assert {"extract", "individual", "global"} <= set(provider.roles)
    assert result.coverage.individually_assessed == 1
    if fail_role:
        assert not result.coverage.complete
        assert not result.coverage.global_pass_complete
        assert result.readiness.verdict == "unable_to_determine"
        assert result.limitations
    else:
        assert "critic" in provider.roles
        assert result.coverage.complete
        assert result.coverage.critic_complete
        matching = [finding for finding in result.findings if finding.kind == "atomicity"]
        assert len(matching) == 1
        assert matching[0].status == "confirmed"
        assert matching[0].severity == "major"
        assert result.readiness.verdict == "requires_revision"


def test_unsubstantiated_critic_cannot_hide_local_placeholder():
    from specguard.core import audit_documents
    from specguard.intelligence import verify

    class RejectingCritic(ScriptedProvider):
        def run(self, role, payload):
            if role != "critic":
                return super().run(role, payload)
            verdicts = super().run(role, payload)
            for verdict in verdicts["verdicts"]:
                verdict.update(
                    verdict="rejected",
                    evidence=[],
                    counterevidence=[],
                    explanation="Предложено скрыть замечание без подтверждения.",
                )
            return verify(role, payload, verdicts)

    doc = ingest_document("scope.md", b"- SG-01: The service must retain logs for TBD days.")
    audit = audit_documents([doc], provider=RejectingCritic())
    finding = next(f for f in audit.findings if f.kind == "unfilled_placeholder")
    assert finding.status == "confirmed" and finding.review_explanation


@pytest.mark.parametrize(
    ("section", "upper_clause", "note", "expected"),
    [
        ("Transport", "8 packets", "", "confirmed"),
        ("Transport", "8 packets in recovery mode", "", "requires_clarification"),
        ("Transport", "8 frames", "", "requires_clarification"),
        ("Transport", "8 packets", "Applies only to test systems.", "requires_clarification"),
        ("Backup", "8 packets", "", "requires_clarification"),
    ],
)
def test_cross_document_bounds_preserve_applicability_and_units(section, upper_clause, note, expected):
    from specguard.core import audit_documents

    lower = "# Transport\n\n- NET-16: Window size must be at least 16 packets."
    upper = f"# {section}\n\n{note}\n\n- NET-24: Window size must be at most {upper_clause}."
    docs = [ingest_document(name, value.encode()) for name, value in [("in.md", lower), ("out.md", upper)]]
    finding = next(item for item in audit_documents(docs).findings if item.kind == "contradiction")
    assert finding.status == expected
    assert {ref.location.document_id for ref in finding.evidence} == {doc.document_id for doc in docs}
