"""Run requirement extraction, assessment, criticism, and evidence verification."""

from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from itertools import combinations
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from . import __version__
from .intelligence import IntelligenceError, verify
from .models import (
    AuditCoverage,
    AuditResult,
    CriterionAssessment,
    DocumentMetadata,
    Evidence,
    Finding,
    Readiness,
    RejectedCandidate,
    Requirement,
    RequirementAssessment,
    SourceBlock,
    SourceDocument,
    UsageRecord,
)
from .rules import deterministic_candidates, original_ids, seed_requirements

SourceKey = tuple[str, str]
Progress = Callable[[str, dict[str, object]], None]
FULL_CONTEXT_BYTES = 43_000
FULL_CONTEXT_REQUIREMENTS = 60
MAX_GLOBAL_WINDOWS = 14
MAX_REQUIREMENTS = 240
MAX_AUDIT_DOCUMENTS = 8
MAX_AUDIT_BLOCKS = 3_000
MAX_CRITIC_CANDIDATES = 150
SEVERITIES = ("critical", "major", "minor", "informational")
CONTRADICTIONS = {"contradiction", "conflict", "противоречие"}
CRITERION_STATUSES_WITHOUT_FINDING = {"requires_clarification", "context_dependent", "insufficient_evidence"}


class AuditError(RuntimeError):
    """The audit cannot run or produce a valid result."""


class SemanticProvider(Protocol):
    records: list[dict]

    def run(self, role: str, payload: dict) -> dict: ...


@lru_cache(maxsize=1)
def revision() -> str:
    root = Path(__file__).resolve().parents[1]
    if (root / ".git").exists():
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return __version__


def _id(prefix: str, *parts: str) -> str:
    return f"{prefix}-{sha256(chr(31).join(parts).encode()).hexdigest()[:24]}"


def _key(block: SourceBlock) -> SourceKey:
    return block.location.document_id, block.block_id


def provider_block(block: SourceBlock) -> dict:
    return {
        "document_id": block.location.document_id,
        "block_id": block.block_id,
        "text": block.text,
        "section": block.section or "",
    }


def provider_evidence(evidence: Evidence) -> dict:
    scope = evidence.scope
    if scope == evidence.location.document_id:
        scope = evidence.location.block_id
    return {
        "document_id": evidence.location.document_id,
        "block_id": evidence.location.block_id,
        "kind": evidence.kind,
        "quote": evidence.quote,
        "scope": scope,
    }


def provider_requirement(requirement: Requirement) -> dict:
    return {
        "requirement_id": requirement.requirement_id,
        "original_id": requirement.original_id,
        "summary": requirement.summary,
        "kind": requirement.kind,
        "section": requirement.section,
        "relationships": requirement.relationships,
        "evidence": [provider_evidence(evidence) for evidence in requirement.evidence],
    }


def provider_finding(finding: Finding) -> dict:
    """Return a grounded finding in the inference provider's DTO format."""
    return {
        "finding_id": finding.finding_id,
        "kind": finding.kind,
        "title": finding.title,
        "description": finding.explanation,
        "criterion": finding.criterion,
        "severity": finding.severity,
        "status": finding.status,
        "requirement_ids": finding.requirement_ids,
        "evidence": [provider_evidence(evidence) for evidence in finding.evidence],
        "impact": finding.impact,
        "recommendation": finding.recommendation,
        "uncertainty": finding.uncertainty or "Не указана.",
        "conflict_scenario": finding.conflict_scenario,
    }


def verify_evidence(
    raw: dict,
    blocks: Mapping[SourceKey, SourceBlock],
    *,
    allowed_scopes: bool = False,
) -> Evidence | None:
    """Resolve an exact quote or a declared, existing absence scope to source coordinates."""
    document_id, block_id = raw.get("document_id"), raw.get("block_id")
    if not isinstance(document_id, str) or not isinstance(block_id, str):
        return None
    block = blocks.get((document_id, block_id))
    if block is None:
        return None
    kind = raw.get("kind", "quote")
    quote, scope = raw.get("quote"), raw.get("scope")
    if kind == "absence":
        permitted = {block_id, block.section}
        if allowed_scopes:
            permitted.add(document_id)
        if quote is not None or not isinstance(scope, str) or not scope or scope not in permitted:
            return None
        return Evidence(
            evidence_id=_id("ev", document_id, block_id, kind, scope),
            kind=kind,
            location=block.location,
            scope=scope,
        )
    if kind != "quote" or not isinstance(quote, str) or not quote.strip():
        return None
    start = block.text.find(quote)
    if start == -1:
        return None
    location = block.location.model_copy()
    if location.char_start is not None:
        location.char_start += start
        location.char_end = location.char_start + len(quote)
    if location.line_start is not None:
        location.line_start += len(re.findall(r"\r\n|[\r\n]", block.text[:start]))
        location.line_end = location.line_start + len(re.findall(r"\r\n|[\r\n]", quote.rstrip("\r\n")))
    return Evidence(
        evidence_id=_id("ev", document_id, block_id, kind, str(start), quote),
        kind=kind,
        location=location,
        quote=quote,
    )


def _evidence_set(raw: Sequence[dict], index: Mapping[SourceKey, SourceBlock], *, local: bool = False):
    evidence = {}
    for cite in raw:
        verified = verify_evidence(cite, index, allowed_scopes=local)
        if verified is None:
            return None
        evidence[verified.evidence_id] = verified
    return list(evidence.values())


def _requirement(raw: dict, index: Mapping[SourceKey, SourceBlock]) -> Requirement | None:
    evidence = _evidence_set(raw["evidence"], index)
    if not evidence or any(item.kind != "quote" for item in evidence):
        return None
    head = evidence[0]
    document_id = head.location.document_id
    if any(item.location.document_id != document_id for item in evidence):
        return None
    original_id = raw.get("original_id")
    if original_id:
        if not any(
            original_id in index[(item.location.document_id, item.location.block_id)].text
            for item in evidence
        ):
            return None
        # Different quotation spans for an explicitly identified clause still share one ID.
        anchor = next(
            (item for item in evidence if original_id in index[(document_id, item.location.block_id)].text),
            head,
        )
        requirement_id = _id("req", document_id, anchor.location.block_id, original_id)
    else:
        requirement_id = _id("req", document_id, *(item.evidence_id for item in evidence))
    return Requirement(
        requirement_id=requirement_id,
        document_id=document_id,
        original_id=original_id,
        kind=raw["kind"],
        summary=raw["summary"],
        section=head.location.section,
        evidence=evidence,
        relationships=raw.get("relationships", []),
        uncertainty=raw.get("uncertainty"),
    )


def _chunks(
    blocks: Sequence[SourceBlock],
    *,
    bytes_limit: int,
    count_limit: int,
) -> list[list[SourceBlock]]:
    groups = []
    current = []
    total = 0
    for block in blocks:
        size = len(block.text.encode()) + len((block.section or "").encode()) + 160
        if current and (total + size > bytes_limit or len(current) >= count_limit):
            groups.append(current)
            current = []
            total = 0
        current.append(block)
        total += size
    if current:
        groups.append(current)
    return groups


def _call(provider: SemanticProvider, role: str, payload: dict, limitations: list[str]) -> dict | None:
    try:
        # The same validation also applies to alternative/mock providers.
        return verify(role, payload, provider.run(role, payload))
    except IntelligenceError as error:
        limitations.append(f"Этап {role}: проверка модели не завершена ({error.code}).")
    except (TimeoutError, OSError):
        limitations.append(f"Этап {role}: провайдер недоступен.")
    return None


def _extract(
    documents: Sequence[SourceDocument],
    index: Mapping[SourceKey, SourceBlock],
    provider: SemanticProvider | None,
    limitations: list[str],
) -> tuple[list[Requirement], int]:
    registry = {}
    reviewed = 0
    all_ids = list(
        dict.fromkeys(
            identifier
            for document in documents
            for block in document.blocks
            for identifier, _ in original_ids(block)
        )
    )
    for document in documents:
        if provider is None:
            groups = [document.blocks]
        else:
            groups = _chunks(document.blocks, bytes_limit=20_000, count_limit=20)
        for blocks in groups:
            seeds = seed_requirements(blocks)
            if provider is None:
                records = seeds
            else:
                result = _call(
                    provider,
                    "extract",
                    {
                        "blocks": [provider_block(block) for block in blocks],
                        "document_name": document.filename,
                        "existing_ids": all_ids,
                    },
                    limitations,
                )
                if result is None:
                    records = seeds
                else:
                    reviewed += len(blocks)
                    records = result["requirements"]
                    recorded = {
                        (entry["original_id"], ref["block_id"])
                        for entry in records
                        if entry["original_id"]
                        for ref in entry["evidence"]
                    }
                    records.extend(
                        seed
                        for seed in seeds
                        if seed["original_id"]
                        and (seed["original_id"], seed["evidence"][0]["block_id"]) not in recorded
                    )
            for raw in records:
                if requirement := _requirement(raw, index):
                    registry.setdefault(requirement.requirement_id, requirement)
    return sorted(
        registry.values(),
        key=lambda item: (
            next(i for i, document in enumerate(documents) if document.document_id == item.document_id),
            item.evidence[0].location.char_start or 0,
        ),
    ), reviewed


def _requirements_by_key(requirements: Sequence[Requirement]) -> dict[SourceKey, set[str]]:
    result: dict[SourceKey, set[str]] = defaultdict(set)
    for requirement in requirements:
        for cite in requirement.evidence:
            result[(cite.location.document_id, cite.location.block_id)].add(requirement.requirement_id)
    return result


def _matches_block(evidence: Evidence, keys: set[SourceKey]) -> bool:
    return (evidence.location.document_id, evidence.location.block_id) in keys


def _role_payload(blocks: Sequence[SourceBlock], requirements: Sequence[Requirement]) -> dict:
    return {
        "blocks": [provider_block(block) for block in blocks],
        "requirements": [provider_requirement(requirement) for requirement in requirements],
    }


def _neighbor_blocks(
    blocks: Sequence[SourceBlock],
    required: set[SourceKey],
    *,
    radius: int = 3,
) -> list[SourceBlock]:
    included = set()
    sections = set()
    for i, block in enumerate(blocks):
        if _key(block) in required:
            sections.add((block.location.document_id, block.section))
            for j in range(max(i - radius, 0), min(i + radius + 1, len(blocks))):
                if blocks[j].location.document_id == block.location.document_id:
                    included.add(j)
    included.update(
        i
        for i, block in enumerate(blocks)
        if block.kind == "heading" and (block.location.document_id, block.section) in sections
    )
    return [block for i, block in enumerate(blocks) if i in included]


def _assessment_pass(
    blocks: Sequence[SourceBlock],
    requirements: Sequence[Requirement],
    provider: SemanticProvider,
    limitations: list[str],
    use_full_context: bool,
) -> dict[str, dict]:
    output = {}
    for start in range(0, min(len(requirements), MAX_REQUIREMENTS), 4):
        batch = requirements[start : start + 4]
        anchors = {
            (cite.location.document_id, cite.location.block_id) for req in batch for cite in req.evidence
        }
        context = blocks if use_full_context else _neighbor_blocks(blocks, anchors)
        result = _call(provider, "individual", _role_payload(context, batch), limitations)
        if result is not None:
            output.update((row["requirement_id"], row) for row in result["assessments"])
    if len(requirements) > MAX_REQUIREMENTS:
        limitations.append(f"Лимит индивидуальной семантической проверки: {MAX_REQUIREMENTS} требований.")
    return output


def _global_windows(
    blocks: Sequence[SourceBlock],
    requirements: Sequence[Requirement],
    use_full_context: bool,
) -> tuple[list[list[SourceBlock]], bool]:
    if use_full_context:
        return [list(blocks)], True
    groups = _chunks(blocks, bytes_limit=28_000, count_limit=36)
    group_for = {_key(block): i for i, group in enumerate(groups) for block in group}
    by_original: dict[str, set[int]] = defaultdict(set)
    for row in requirements:
        if row.original_id:
            location = row.evidence[0].location
            by_original[row.original_id.casefold()].add(group_for[(location.document_id, location.block_id)])
    scores: dict[tuple[int, int], int] = defaultdict(int)
    for row in requirements:
        location = row.evidence[0].location
        source = group_for[(location.document_id, location.block_id)]
        for link in row.relationships:
            for target in by_original[link.casefold()] - {source}:
                scores[tuple(sorted((source, target)))] += 1
    pairs = combinations(range(len(groups)), 2)
    ordered = sorted(pairs, key=lambda pair: (-scores[pair], pair[1] - pair[0], pair))
    room = max(MAX_GLOBAL_WINDOWS - len(groups), 0)
    windows = groups + [groups[left] + groups[right] for left, right in ordered[:room]]
    return windows[:MAX_GLOBAL_WINDOWS], len(groups) + len(ordered) <= MAX_GLOBAL_WINDOWS


def _global_pass(
    blocks: Sequence[SourceBlock],
    requirements: Sequence[Requirement],
    provider: SemanticProvider,
    limitations: list[str],
    use_full_context: bool,
    individual_candidates: Sequence[dict],
) -> tuple[list[dict], bool]:
    output = []
    # The global role has a larger context budget than a single requirement pass.
    # Keep linked specifications together when the actual serialized registry fits.
    if not use_full_context and len(blocks) <= 500:
        combined = _role_payload(blocks, requirements)
        combined["candidates"] = list(individual_candidates[:32])
        use_full_context = len(json.dumps(combined, ensure_ascii=False).encode("utf-8")) <= 240_000
    windows, complete = _global_windows(blocks, requirements, use_full_context)
    if not complete:
        limitations.append("Глобальный анализ ограничен по объёму: часть пар разделов не проверена.")
    for context in windows:
        keys = {_key(block) for block in context}
        registry = [req for req in requirements if all(_matches_block(cite, keys) for cite in req.evidence)]
        ids = {r.requirement_id for r in registry}
        payload = _role_payload(context, registry)
        payload["candidates"] = [
            item
            for item in individual_candidates
            if set(item["requirement_ids"]) <= ids
            and all((e["document_id"], e["block_id"]) in keys for e in item["evidence"])
        ][:32]
        result = _call(provider, "global", payload, limitations)
        if result is None:
            complete = False
        else:
            output.extend(result["findings"])
    return output, complete


def _candidate_finding(
    raw: dict,
    scope: str,
    local: bool,
    index: Mapping[SourceKey, SourceBlock],
    related: Mapping[SourceKey, set[str]],
    requirement_ids: set[str],
) -> tuple[str, Finding | None, str | None]:
    evidence = _evidence_set(raw["evidence"], index, local=local)
    kind = raw["kind"].casefold()
    candidate_id = _id("candidate", kind, raw["title"], *(item.evidence_id for item in (evidence or [])))
    if not evidence:
        return candidate_id, None, "Ссылка на источник или точная цитата не прошла проверку."
    if not set(raw["requirement_ids"]) <= requirement_ids:
        return candidate_id, None, "Неизвестный идентификатор требования."
    scenario = raw.get("conflict_scenario")
    quotes = [item for item in evidence if item.kind == "quote"]
    if kind in CONTRADICTIONS and (
        len(quotes) < 2
        or not scenario
        or all(
            left.location.document_id == right.location.document_id
            and left.location.block_id == right.location.block_id
            and max(left.location.char_start or 0, right.location.char_start or 0)
            < min(left.location.char_end or 0, right.location.char_end or 0)
            for left, right in combinations(quotes, 2)
        )
    ):
        return candidate_id, None, "Для противоречия нужны две отдельные цитаты и сценарий конфликта."
    linked = set(raw["requirement_ids"])
    for cite in evidence:
        if cite.kind == "quote":
            linked.update(related.get((cite.location.document_id, cite.location.block_id), set()))
    status = raw["status"]
    if not local and any(item.kind == "absence" for item in evidence) and status == "confirmed":
        status = "requires_clarification"
    finding = Finding(
        finding_id=_id("finding", kind, *(sorted(item.evidence_id for item in evidence))),
        kind=kind,
        scope=scope,
        title=raw["title"],
        explanation=raw["description"],
        criterion=raw.get("criterion") or kind,
        severity=raw["severity"],
        status=status,
        document_ids=list(dict.fromkeys(cite.location.document_id for cite in evidence)),
        requirement_ids=sorted(linked),
        evidence=evidence,
        impact=raw["impact"],
        recommendation=raw["recommendation"],
        uncertainty=raw.get("uncertainty"),
        conflict_scenario=scenario,
    )
    return candidate_id, finding, None


def _is_duplicate(left: Finding, right: Finding) -> bool:
    if left.kind != right.kind and not (left.kind in CONTRADICTIONS and right.kind in CONTRADICTIONS):
        return False
    if left.finding_id == right.finding_id:
        return True
    left_quotes = [cite for cite in left.evidence if cite.quote]
    right_quotes = [cite for cite in right.evidence if cite.quote]
    if not left_quotes or not right_quotes:
        return False
    matches = [
        (left_ref, right_ref)
        for left_ref in left_quotes
        for right_ref in right_quotes
        if left_ref.location.document_id == right_ref.location.document_id
        and left_ref.location.block_id == right_ref.location.block_id
        and (left_ref.quote in right_ref.quote or right_ref.quote in left_ref.quote)
    ]
    return len({left_ref.evidence_id for left_ref, _ in matches}) == len(left_quotes) and len(
        {right_ref.evidence_id for _, right_ref in matches}
    ) == len(right_quotes)


def _collect_candidates(
    raw: Sequence[tuple[dict, str, bool]],
    requirements: Sequence[Requirement],
    index: Mapping[SourceKey, SourceBlock],
) -> tuple[list[tuple[str, Finding, bool]], list[RejectedCandidate]]:
    accepted = []
    by_kind: dict[str, list[Finding]] = defaultdict(list)
    rejected = []
    related = _requirements_by_key(requirements)
    requirement_ids = {item.requirement_id for item in requirements}
    for candidate, scope, local in raw:
        candidate_id, finding, reason = _candidate_finding(
            candidate, scope, local, index, related, requirement_ids
        )
        kind = candidate["kind"].casefold()
        group = "contradiction" if kind in CONTRADICTIONS else kind
        if finding is None:
            rejected.append(
                RejectedCandidate(
                    candidate_id=candidate_id,
                    kind=kind,
                    title=candidate["title"],
                    reason=reason,
                    status="unsupported",
                )
            )
        elif any(_is_duplicate(finding, existing) for existing in by_kind[group]):
            rejected.append(
                RejectedCandidate(
                    candidate_id=candidate_id,
                    kind=kind,
                    title=finding.title,
                    status="duplicate",
                    reason="Кандидат повторяет нарушение с тем же подтверждающим фрагментом.",
                )
            )
        else:
            accepted.append((candidate_id, finding, local))
            by_kind[group].append(finding)
    return accepted, rejected


def _critic_pass(
    candidates: Sequence[tuple[str, Finding, bool]],
    blocks: Sequence[SourceBlock],
    requirements: Sequence[Requirement],
    provider: SemanticProvider,
    limitations: list[str],
    use_full_context: bool,
) -> tuple[dict[str, dict], bool]:
    reviewed = {}
    complete = len(candidates) <= MAX_CRITIC_CANDIDATES
    if not complete:
        limitations.append(f"Лимит независимой проверки: {MAX_CRITIC_CANDIDATES} кандидатов.")
    for start in range(0, min(len(candidates), MAX_CRITIC_CANDIDATES), 5):
        batch = candidates[start : start + 5]
        linked = {requirement_id for _, item, _ in batch for requirement_id in item.requirement_ids}
        registry = [req for req in requirements if req.requirement_id in linked]
        anchors = {
            (cite.location.document_id, cite.location.block_id)
            for _, item, _ in batch
            for cite in item.evidence
        }
        anchors.update(
            (cite.location.document_id, cite.location.block_id) for req in registry for cite in req.evidence
        )
        context = blocks if use_full_context else _neighbor_blocks(blocks, anchors)
        payload = _role_payload(context, registry)
        payload["candidates"] = []
        for candidate_id, finding, _ in batch:
            item = provider_finding(finding)
            item.pop("finding_id")
            item["candidate_id"] = candidate_id
            item["evidence"] = item["evidence"][:60]
            payload["candidates"].append(item)
        result = _call(provider, "critic", payload, limitations)
        if result is None:
            complete = False
        else:
            reviewed.update((review["candidate_id"], review) for review in result["verdicts"])
    return reviewed, complete


def _adjudicate(
    candidates: Sequence[tuple[str, Finding, bool]],
    verdicts: Mapping[str, dict],
    index: Mapping[SourceKey, SourceBlock],
    rejected: list[RejectedCandidate],
) -> list[Finding]:
    findings = []
    by_id = {cid: item for cid, item, _ in candidates}
    for candidate_id, finding, local in candidates:
        verdict = verdicts.get(candidate_id)
        if verdict is None:
            if local:
                findings.append(finding)
            else:
                rejected.append(
                    RejectedCandidate(
                        candidate_id=candidate_id,
                        kind=finding.kind,
                        title=finding.title,
                        reason="Нет завершённого решения независимого рецензента.",
                        status="unsupported",
                    )
                )
            continue
        decision = verdict["verdict"]
        if decision in {"rejected", "duplicate"}:
            counter = _evidence_set(verdict["counterevidence"], index) or []
            other = by_id.get(verdict.get("duplicate_of"))
            linked_duplicate = other is not None and _is_duplicate(finding, other)
            if local or (decision == "duplicate" and not linked_duplicate):
                # The critic may disagree with a reproducible local observation.
                # Keep its evidence available for human resolution.
                updated = {"review_explanation": verdict["explanation"], "counterevidence": counter}
                if not local or counter:
                    updated["status"] = "requires_clarification"
                findings.append(finding.model_copy(update=updated))
                continue
            rejected.append(
                RejectedCandidate(
                    candidate_id=candidate_id,
                    kind=finding.kind,
                    title=finding.title,
                    reason=verdict["explanation"],
                    status=decision,
                )
            )
            continue
        evidence = _evidence_set(verdict["evidence"], index)
        counterevidence = _evidence_set(verdict["counterevidence"], index)
        if evidence is None or counterevidence is None:
            rejected.append(
                RejectedCandidate(
                    candidate_id=candidate_id,
                    kind=finding.kind,
                    title=finding.title,
                    reason="Цитаты независимого рецензента не подтверждены источником.",
                    status="unsupported",
                )
            )
            continue
        support = {cite.evidence_id: cite for cite in [*finding.evidence, *evidence]}
        status = finding.status
        if decision == "requires_clarification" and status == "confirmed" and (not local or counterevidence):
            status = decision
        if status == "confirmed" and not local and not any(item.kind == "quote" for item in evidence):
            status = "requires_clarification"
        severity = finding.severity
        if not local and SEVERITIES.index(verdict["severity"]) > SEVERITIES.index(severity):
            severity = verdict["severity"]
        findings.append(
            finding.model_copy(
                update={
                    "status": status,
                    "severity": severity,
                    "review_explanation": verdict["explanation"],
                    "counterevidence": counterevidence,
                    "evidence": list(support.values()),
                    "document_ids": list(
                        dict.fromkeys(cite.location.document_id for cite in support.values())
                    ),
                }
            )
        )
    return findings


def _risk_pass(findings, blocks, requirements, provider, limitations):
    verified = [f for f in findings if f.status == "confirmed"]
    for start in range(0, min(len(verified), MAX_CRITIC_CANDIDATES), 5):
        batch = verified[start : start + 5]
        ids = {i for f in batch for i in f.requirement_ids}
        registry = [r for r in requirements if r.requirement_id in ids]
        anchors = {
            (e.location.document_id, e.location.block_id) for row in [*batch, *registry] for e in row.evidence
        }
        payload = _role_payload(_neighbor_blocks(blocks, anchors), registry)
        payload["findings"] = [provider_finding(f) for f in batch]
        result = _call(provider, "risk", payload, limitations)
        if result:
            impacts = {row["finding_id"]: row["impact"] for row in result["risks"]}
            for finding in batch:
                finding.impact = impacts[finding.finding_id]


def _assessments(
    requirements: Sequence[Requirement],
    rows: Mapping[str, dict],
    findings: Sequence[Finding],
    live: bool,
) -> list[RequirementAssessment]:
    by_requirement: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        for requirement_id in finding.requirement_ids:
            by_requirement[requirement_id].append(finding)
    assessments = []
    for requirement in requirements:
        req_id = requirement.requirement_id
        attached = by_requirement[req_id]
        row = rows.get(req_id)
        criteria = []
        if row:
            proven = {finding.criterion for finding in attached if finding.status == "confirmed"}
            for criterion in row["criteria"]:
                result = CriterionAssessment.model_validate(criterion)
                if result.status == "confirmed_defect" and result.criterion not in proven:
                    result.status = "requires_clarification"
                    result.explanation = (
                        "Для вывода о нарушении критерия требуется дополнительное подтверждение."
                    )
                criteria.append(result)
        assessments.append(
            RequirementAssessment(
                requirement_id=req_id,
                status="complete" if row else "incomplete" if live else "offline",
                criteria=criteria,
                finding_ids=[finding.finding_id for finding in attached],
                uncertainty=row["uncertainty"] if row else None,
            )
        )
    return assessments


def assess_readiness(
    findings: Sequence[Finding],
    coverage: AuditCoverage,
    assessments: Sequence[RequirementAssessment] = (),
) -> Readiness:
    """Apply explicit readiness rules independently from model recommendations."""
    levels = dict.fromkeys(SEVERITIES, 0)
    unresolved = [finding for finding in findings if finding.status != "confirmed"]
    for finding in findings:
        if finding.status == "confirmed":
            levels[finding.severity] += 1
    unresolved_criteria = sum(
        any(criterion.status in CRITERION_STATUSES_WITHOUT_FINDING for criterion in assessment.criteria)
        for assessment in assessments
    )
    if not coverage.complete:
        verdict = "unable_to_determine"
        rationale = "Проверка не завершена. Обнаруженные дефекты доступны для исправления."
    elif levels["critical"] or levels["major"]:
        verdict = "requires_revision"
        rationale = "Подтверждён критический или существенный дефект, влияющий на реализацию либо проверку."
    elif levels["minor"] or unresolved or unresolved_criteria:
        verdict = "ready_with_conditions"
        rationale = (
            "Разработку и тестирование можно планировать с учётом перечисленных исправлений и уточнений."
        )
    else:
        verdict = "ready"
        rationale = (
            "Проверка завершена. Не выявлено дефектов или открытых вопросов, блокирующих начало работ."
        )
    ordered = sorted(
        (item for item in findings if item.severity != "informational" or item.status != "confirmed"),
        key=lambda item: (item.status != "confirmed", SEVERITIES.index(item.severity), item.finding_id),
    )
    return Readiness(
        verdict=verdict,
        rationale=rationale,
        confirmed_by_severity=levels,
        clarification_count=len(unresolved),
        priority_finding_ids=[item.finding_id for item in ordered],
    )


def _usage(provider: SemanticProvider | None) -> list[UsageRecord]:
    if provider is None:
        return []
    return [
        UsageRecord(
            role=record["role"],
            model=record.get("model"),
            prompt_version=record.get("prompt_version"),
            attempt=record.get("attempt"),
            status=record.get("status"),
            input_tokens=record.get("input_tokens"),
            output_tokens=record.get("output_tokens"),
            reasoning_tokens=record.get("reasoning_tokens"),
            latency_ms=record.get("duration_ms", record.get("latency_ms")),
        )
        for record in getattr(provider, "records", [])
    ]


def audit_documents(
    documents: Sequence[SourceDocument],
    provider: SemanticProvider | None = None,
    *,
    progress: Progress | None = None,
    audit_id: str | None = None,
) -> AuditResult:
    """Run the common audit service on immutable parsed source records."""
    documents = list({document.document_id: document for document in reversed(documents)}.values())[::-1]
    if not documents or len(documents) > MAX_AUDIT_DOCUMENTS:
        raise AuditError(f"Для одного аудита требуется от 1 до {MAX_AUDIT_DOCUMENTS} документов.")
    blocks = [block for document in documents for block in document.blocks]
    if len(blocks) > MAX_AUDIT_BLOCKS:
        raise AuditError(f"В одном аудите допустимо не более {MAX_AUDIT_BLOCKS} текстовых блоков.")
    started = datetime.now(timezone.utc)
    index = {_key(block): block for block in blocks}
    limitations = [
        f"{document.filename}: {warning}" for document in documents for warning in document.warnings
    ]
    if progress:
        progress("extracting", {"document_ids": [document.document_id for document in documents]})
    requirements, extraction_reviewed = _extract(documents, index, provider, limitations)
    raw = [
        (candidate, candidate["scope"], True)
        for candidate in deterministic_candidates(documents, requirements)
    ]
    rows = {}
    global_complete = False
    critic_complete = False
    verdicts = {}
    if provider is None:
        limitations.append(
            "Локальный режим: выполнены формальные проверки. Семантическая проверка не проводилась."
        )
    else:
        use_full_context = (
            len(blocks) <= 100
            and len(requirements) <= FULL_CONTEXT_REQUIREMENTS
            and sum(len(block.text.encode()) + len((block.section or "").encode()) + 160 for block in blocks)
            <= FULL_CONTEXT_BYTES
        )
        if requirements:
            if progress:
                progress("validating_individual", {"requirement_count": len(requirements)})
            rows = _assessment_pass(blocks, requirements, provider, limitations, use_full_context)
            raw.extend(
                (candidate, "individual", False) for row in rows.values() for candidate in row["findings"]
            )
        else:
            limitations.append("Не удалось выделить требования для индивидуальной проверки.")
        if progress:
            progress("validating_global", {"document_count": len(documents)})
        globals_found, global_complete = _global_pass(
            blocks,
            requirements,
            provider,
            limitations,
            use_full_context,
            [item for item, scope, local in raw if scope == "individual" and not local],
        )
        raw.extend((candidate, "global", False) for candidate in globals_found)
    if progress:
        progress("verifying_evidence", {"candidate_count": len(raw)})
    candidates, rejected = _collect_candidates(raw, requirements, index)
    if provider is not None:
        verdicts, critic_complete = _critic_pass(
            candidates,
            blocks,
            requirements,
            provider,
            limitations,
            use_full_context,
        )
    findings = _adjudicate(candidates, verdicts, index, rejected)
    if provider is not None:
        _risk_pass(findings, blocks, requirements, provider, limitations)
    for finding in findings:
        if progress and finding.kind in CONTRADICTIONS and finding.status == "confirmed":
            progress("contradiction_detected", {"finding_ids": [finding.finding_id]})

    assessments = _assessments(requirements, rows, findings, provider is not None)
    coverage = AuditCoverage(
        source_blocks=len(blocks),
        extraction_blocks_reviewed=extraction_reviewed,
        requirements=len(requirements),
        individually_assessed=len(rows),
        global_pass_complete=global_complete,
        critic_complete=critic_complete,
        complete=(
            provider is not None
            and bool(requirements)
            and extraction_reviewed == len(blocks)
            and len(rows) == len(requirements)
            and global_complete
            and critic_complete
            and not any(document.warnings for document in documents)
        ),
    )
    readiness = assess_readiness(findings, coverage, assessments)
    usage = _usage(provider)
    model_names = list(dict.fromkeys(record.model for record in usage if record.model))
    return AuditResult(
        audit_id=audit_id or uuid4().hex,
        created_at=started,
        agent_version=revision(),
        model=", ".join(model_names)
        if model_names
        else ("Модель не отчиталась" if provider else "Без модели"),
        mode="live" if provider is not None else "offline",
        documents=[
            DocumentMetadata.model_validate(doc.model_dump(exclude={"blocks", "original_text"}))
            for doc in documents
        ],
        requirements=requirements,
        assessments=assessments,
        findings=findings,
        rejected_candidates=rejected,
        readiness=readiness,
        coverage=coverage,
        usage=usage,
        limitations=list(dict.fromkeys(limitations)),
    )
