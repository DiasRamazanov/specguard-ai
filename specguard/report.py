"""Render the same audit result as a Russian report or structured JSON."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .models import AuditResult, Evidence, Finding

_SEVERITY = {
    "critical": "Критический",
    "major": "Существенный",
    "minor": "Незначительный",
    "informational": "Информационное замечание",
}
_STATUS = {
    "confirmed": "Подтверждено",
    "requires_clarification": "Требует уточнения",
    "context_dependent": "Зависит от контекста",
    "valid": "Нарушение не выявлено",
    "confirmed_defect": "Подтверждён дефект",
    "insufficient_evidence": "Недостаточно данных",
    "not_applicable": "Неприменимо",
}
_CRITERIA = {
    "necessity": "Необходимость",
    "appropriateness": "Уместность",
    "unambiguity": "Однозначность",
    "completeness": "Полнота",
    "singularity": "Атомарность",
    "feasibility": "Реализуемость",
    "verifiability": "Проверяемость",
    "correctness": "Корректность",
    "conformance": "Соответствие соглашениям",
    "consistency": "Согласованность",
    "traceability": "Прослеживаемость",
}
_VERDICT = {
    "ready": "Готово",
    "ready_with_conditions": "Готово с условиями",
    "requires_revision": "Требуется доработка",
    "unable_to_determine": "Невозможно определить готовность",
}
_CHECK = {
    "complete": "Семантическая проверка выполнена",
    "incomplete": "Семантическая проверка не завершена",
    "offline": "Выполнены только локальные формальные проверки",
}
_ROLE = {
    "extract": "Извлечение",
    "individual": "Отдельные требования",
    "global": "Набор требований",
    "critic": "Независимая проверка",
}
_REJECTED = {"unsupported": "Не подтверждено источником", "duplicate": "Дубликат", "rejected": "Отклонено"}


def _md(value: str) -> str:
    flat = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"([\\`*_{}\[\]()<>#!+|~])", r"\\\1", flat)


def _location(evidence: Evidence, documents: Mapping[str, str]) -> str:
    loc = evidence.location
    parts = [_md(documents[loc.document_id])]
    if loc.page:
        parts.append(f"стр. {loc.page}")
    if loc.line_start:
        end = f"–{loc.line_end}" if loc.line_end and loc.line_end != loc.line_start else ""
        parts.append(f"строка {loc.line_start}{end}")
    if loc.section:
        parts.append(f"раздел «{_md(loc.section)}»")
    parts.append(f"`{loc.block_id}`")
    return ", ".join(parts)


def _source(evidence: Evidence, documents: Mapping[str, str]) -> list[str]:
    location = _location(evidence, documents)
    if evidence.kind == "absence":
        scope = evidence.scope
        if scope == evidence.location.document_id:
            scope = "документ целиком"
        return [f"- Область проверки отсутствия «{_md(scope or 'указанный фрагмент')}» ({location})."]
    quote = evidence.quote or ""
    fence = "`" * max([3, *(len(run) + 1 for run in re.findall(r"`+", quote))])
    return [f"Источник: {location}.", "", fence + "text", quote, fence]


def _finding(finding: Finding, documents: Mapping[str, str], heading: str = "####") -> list[str]:
    result = [
        f"{heading} {_md(finding.title)}",
        "",
        f"`{finding.finding_id}` · {_SEVERITY[finding.severity]} · {_STATUS[finding.status]}",
        "",
        f"**Критерий** — {_md(_CRITERIA.get(finding.criterion, finding.criterion))}.",
        "",
        _md(finding.explanation),
        "",
        f"**Влияние** — {_md(finding.impact)}",
        "",
        f"**Исправление** — {_md(finding.recommendation)}",
        "",
    ]
    if finding.conflict_scenario:
        result.extend([f"**Сценарий конфликта** — {_md(finding.conflict_scenario)}", ""])
    if finding.requirement_ids:
        linked = ", ".join(f"`{item}`" for item in finding.requirement_ids)
        result.extend([f"**Связанные требования** — {linked}.", ""])
    for evidence in finding.evidence:
        result.extend([*_source(evidence, documents), ""])
    if finding.review_explanation:
        result.extend([f"**Решение рецензента** — {_md(finding.review_explanation)}", ""])
    if finding.counterevidence:
        result.extend(["**Фрагменты в пользу альтернативной трактовки**", ""])
        for evidence in finding.counterevidence:
            result.extend([*_source(evidence, documents), ""])
    return result


def render_markdown(result: AuditResult) -> str:
    documents = {doc.document_id: doc.filename for doc in result.documents}
    lines = [
        "# Отчёт о проверке требований",
        "",
        "## 1. Паспорт прогона",
        "",
        f"- Документы: {', '.join(_md(name) for name in documents.values())}",
        f"- Дата и время (UTC): {result.created_at:%Y-%m-%d %H:%M:%S}",
        f"- Модель: {_md(result.model)}",
        f"- Версия агента: {_md(result.agent_version)}",
        f"- Идентификатор: `{result.audit_id}`",
        f"- Режим: {'семантический и формальный' if result.mode == 'live' else 'локальный формальный'}",
    ]
    for document in result.documents:
        lines.append(f"- SHA-256 для «{_md(document.filename)}»: `{document.sha256}`")
    prompt_versions = ", ".join(
        dict.fromkeys(row.prompt_version for row in result.usage if row.prompt_version)
    )
    if prompt_versions:
        lines.append(f"- Версии промптов: {_md(prompt_versions)}")
    lines.extend(
        [
            "",
            "## 2. Реестр требований",
            "",
            "| Внутренний ID | ID в документе | Краткая формулировка | Цитата | Место |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for req in result.requirements:
        quotes = " / ".join(f"«{_md(cite.quote or '')}»" for cite in req.evidence)
        locations = "; ".join(_location(cite, documents) for cite in req.evidence)
        original_id = _md(req.original_id) if req.original_id else "—"
        lines.append(
            f"| `{req.requirement_id}` | {original_id} | {_md(req.summary)} | {quotes} | {locations} |"
        )
    if not result.requirements:
        lines.extend(["", "Требования для проверки не выделены."])
    lines.extend(["", "## 3. Проверка каждого требования", ""])

    requirements = {req.requirement_id: req for req in result.requirements}
    findings = {finding.finding_id: finding for finding in result.findings}
    included = set()
    for assessment in result.assessments:
        req = requirements[assessment.requirement_id]
        lines.extend(
            [
                f"### `{req.requirement_id}` — {_md(req.summary)}",
                "",
                f"**Статус** — {_CHECK[assessment.status]}.",
                "",
            ]
        )
        for evidence in req.evidence:
            lines.extend([*_source(evidence, documents), ""])
        if assessment.criteria:
            lines.extend(["| Критерий | Результат | Обоснование |", "| --- | --- | --- |"])
            for item in assessment.criteria:
                name = _CRITERIA.get(item.criterion, item.criterion)
                lines.append(f"| {_md(name)} | {_STATUS[item.status]} | {_md(item.explanation)} |")
            lines.append("")
        for finding_id in assessment.finding_ids:
            finding = findings[finding_id]
            if finding.scope == "individual" and finding_id not in included:
                lines.extend(_finding(finding, documents))
                included.add(finding_id)
            else:
                lines.append(f"- Связанное замечание `{finding_id}` — {_md(finding.title)}.")
        if assessment.finding_ids:
            lines.append("")
        elif assessment.status == "complete":
            lines.extend(["Подтверждённые дефекты и замечания с проверенными источниками отсутствуют.", ""])
    for finding in result.findings:
        if finding.scope == "individual" and finding.finding_id not in included:
            lines.extend(_finding(finding, documents, "###"))

    lines.extend(["## 4. Проверка набора требований в целом", ""])
    cov = result.coverage
    lines.extend(
        [
            f"- Семантический обзор источника: {cov.extraction_blocks_reviewed} из {cov.source_blocks} блоков.",
            f"- Индивидуальная семантическая проверка: {cov.individually_assessed} из {cov.requirements} требований.",
            f"- Глобальная семантическая проверка: {'завершена' if cov.global_pass_complete else 'не завершена'}.",
            f"- Независимая проверка кандидатов: {'завершена' if cov.critic_complete else 'не завершена'}.",
            "",
        ]
    )
    global_findings = [finding for finding in result.findings if finding.scope == "global"]
    for finding in global_findings:
        lines.extend(_finding(finding, documents, "###"))
    if not global_findings:
        lines.extend(["Нет итоговых замечаний по набору требований.", ""])
    if result.rejected_candidates:
        lines.extend(["### Решения по отклонённым и повторным кандидатам", ""])
        for item in result.rejected_candidates:
            lines.append(
                f"- `{item.candidate_id}` · {_REJECTED[item.status]} · {_md(item.title)}. {_md(item.reason)}"
            )
        lines.append("")
    if result.limitations:
        lines.extend(["### Ограничения прогона", ""])
        lines.extend(f"- {_md(item)}" for item in result.limitations)
        lines.append("")

    readiness = result.readiness
    counts = readiness.confirmed_by_severity
    critical = [
        finding
        for finding in result.findings
        if finding.status == "confirmed" and finding.severity == "critical"
    ]
    lines.extend(
        [
            "## 5. Сводка",
            "",
            f"- Выделено требований: {len(result.requirements)}.",
            f"- Подтверждено дефектов: {counts['critical'] + counts['major'] + counts['minor']}.",
            f"- Критических: {counts['critical']}. Существенных: {counts['major']}. Незначительных: {counts['minor']}.",
            f"- Информационных замечаний: {counts['informational']}.",
            f"- Открытых уточнений по замечаниям: {readiness.clarification_count}.",
            "",
            "### Критические дефекты",
            "",
        ]
    )
    if critical:
        lines.extend(f"- `{finding.finding_id}` — {_md(finding.title)}." for finding in critical)
    else:
        lines.append("В выполненных проверках критические дефекты не подтверждены.")
    if result.usage:
        lines.extend(
            [
                "",
                "### Использование модели",
                "",
                "| Этап | Модель | Попытка | Вход | Рассуждение | Выход с рассуждением | Результат |",
                "| --- | --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for row in result.usage:
            stat = "Проверено" if row.status == "validated" else _md(row.status or "Неизвестно")
            counts = [
                str(value) if value is not None else "—"
                for value in (
                    row.attempt,
                    row.input_tokens,
                    row.reasoning_tokens,
                    row.output_tokens,
                )
            ]
            lines.append(
                f"| {_ROLE.get(row.role, _md(row.role))} | {_md(row.model or '—')} | {' | '.join(counts)} | {stat} |"
            )

    lines.extend(
        [
            "",
            "## 6. Итог",
            "",
            f"**Готовность к разработке и тестированию — {_VERDICT[readiness.verdict].lower()}.**",
            "",
            readiness.rationale,
            "",
            "### Приоритет исправлений",
            "",
        ]
    )
    if readiness.priority_finding_ids:
        for index, finding_id in enumerate(readiness.priority_finding_ids, 1):
            finding = findings[finding_id]
            lines.append(
                f"{index}. `{finding.finding_id}` — {_md(finding.title)}. {_md(finding.recommendation)}"
            )
    else:
        lines.append("Приоритетных исправлений по результатам выполненных проверок нет.")
    return "\n".join(lines) + "\n"


def render_json(result: AuditResult) -> str:
    return result.model_dump_json(indent=2) + "\n"
