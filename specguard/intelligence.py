"""Versioned contracts and source verification for independent DeepSeek calls."""

# ruff: noqa: UP045 -- keep Optional runtime annotations importable on Python 3.9.
import json
import re
from pathlib import Path
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, ValidationError
from pydantic.json_schema import models_json_schema

from .provider import DeepSeek, IntelligenceError

VERSION = "v1"
PROMPTS = Path(__file__).parent / "prompts" / VERSION
Text = Annotated[str, StringConstraints(min_length=1, max_length=12000, pattern=r"\S")]
Id = Annotated[str, StringConstraints(min_length=1, max_length=200, pattern=r"\S")]
Severity = Literal["critical", "major", "minor", "informational"]
Criterion = Literal[
    "necessity",
    "appropriateness",
    "unambiguity",
    "completeness",
    "singularity",
    "feasibility",
    "verifiability",
    "correctness",
    "conformance",
]
CRITERIA = [
    "necessity",
    "appropriateness",
    "unambiguity",
    "completeness",
    "singularity",
    "feasibility",
    "verifiability",
    "correctness",
    "conformance",
]


def strict_true(value):
    if value is not True:
        raise ValueError("requires_explicit_true")
    return True


Approval = Annotated[Literal[True], BeforeValidator(strict_true)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Ref(Contract):
    document_id: Id
    block_id: Id


class Block(Ref):
    text: Annotated[str, StringConstraints(min_length=1, max_length=100000)]
    section: Optional[str] = None


class Evidence(Ref):
    quote: Optional[Text]
    kind: Literal["quote", "absence"] = "quote"
    scope: Optional[Text] = None


Citations = Annotated[list[Evidence], Field(min_length=1, max_length=60)]


class RegistryEntry(Contract):
    requirement_id: Id
    evidence: Citations
    original_id: Optional[Id] = None
    summary: Optional[Text] = None
    kind: Optional[Id] = None
    section: Optional[str] = None
    relationships: list[Id] = Field(default_factory=list)


class Candidate(Contract):
    kind: Id
    title: Text
    description: Text
    severity: Severity
    status: Literal["confirmed", "requires_clarification", "context_dependent"]
    criterion: Optional[Text] = None
    requirement_ids: list[Id]
    evidence: Citations
    impact: Text
    recommendation: Text
    uncertainty: Text
    conflict_scenario: Optional[Text] = None


class ReviewCandidate(Candidate):
    candidate_id: Id


class KnownFinding(Candidate):
    finding_id: Id


class Sources(Contract):
    blocks: Annotated[list[Block], Field(min_length=1, max_length=3000)]


class SourceMetadata(Contract):
    document_id: Id
    filename: Text
    format: Literal["markdown", "pdf", "text"]
    page_count: Optional[Annotated[int, Field(ge=1)]] = None


class ExtractInput(Sources):
    metadata: Optional[SourceMetadata] = None
    document_name: Optional[Text] = None
    existing_ids: list[Id] = Field(default_factory=list)


class RegistryInput(Sources):
    requirements: list[RegistryEntry]
    business_context: Optional[Text] = None


class IndividualInput(RegistryInput):
    criteria: Annotated[list[Criterion], Field(min_length=1)] = Field(default_factory=lambda: list(CRITERIA))


class GlobalInput(RegistryInput):
    candidates: list[Candidate] = Field(default_factory=list)


class CriticInput(RegistryInput):
    candidates: Annotated[list[ReviewCandidate], Field(min_length=1)]


class RiskInput(RegistryInput):
    findings: Annotated[list[KnownFinding], Field(min_length=1)]


class HistoryItem(Contract):
    role: Literal["user", "assistant"]
    content: Text


class ContextInput(Sources):
    requirements: list[RegistryEntry] = Field(default_factory=list)
    findings: list[KnownFinding] = Field(default_factory=list)
    business_context: Optional[Text] = None


class CopilotInput(ContextInput):
    question: Text
    selected_requirement_id: Optional[Id] = None
    selected_finding_id: Optional[Id] = None
    history: Annotated[list[HistoryItem], Field(max_length=12)] = Field(default_factory=list)
    supported_actions: list[Id] = Field(default_factory=list)
    complex: bool = False


class RevisionInput(RiskInput):
    target_requirement_id: Id
    approved_assumptions: list[Text] = Field(default_factory=list)


class CompareInput(ContextInput):
    primary_document_id: Id
    supplementary_document_ids: Annotated[list[Id], Field(min_length=1)]
    purpose: Text


class BenchmarkInput(Contract):
    purpose: Text
    cases: Annotated[int, Field(ge=2, le=12)] = 2
    topics: list[Text] = Field(default_factory=list)


class Extracted(Contract):
    original_id: Optional[Id]
    evidence: Citations
    summary: Text
    kind: Literal[
        "functional", "non_functional", "business_rule", "data", "api", "integration", "acceptance", "process"
    ]
    section: str
    relationships: list[Id]
    uncertainty: Text


class Inventory(Contract):
    requirements: list[Extracted]
    unclassified: list[Ref]


class CriterionAssessment(Contract):
    criterion: Criterion
    status: Literal[
        "valid",
        "confirmed_defect",
        "requires_clarification",
        "context_dependent",
        "insufficient_evidence",
        "not_applicable",
    ]
    explanation: Text


class Assessment(Contract):
    requirement_id: Id
    criteria: list[CriterionAssessment]
    findings: list[Candidate]
    uncertainty: Text


class IndividualResult(Contract):
    assessments: list[Assessment]


class GlobalResult(Contract):
    findings: list[Candidate]


class Verdict(Contract):
    candidate_id: Id
    verdict: Literal["confirmed", "requires_clarification", "rejected", "duplicate"]
    evidence: list[Evidence]
    counterevidence: list[Evidence]
    severity: Severity
    explanation: Text
    uncertainty: Text
    action: Text
    duplicate_of: Optional[Id] = None


class CriticResult(Contract):
    verdicts: list[Verdict]


class Risk(Contract):
    finding_id: Id
    impact: Text
    stakeholders: Annotated[list[Text], Field(min_length=1)]
    priority: Text
    evidence: Citations
    uncertainty: Text


class RiskResult(Contract):
    risks: list[Risk]


class CopilotResult(Contract):
    answer: Text
    evidence: list[Evidence]
    related_finding_ids: list[Id]
    questions: list[Text]
    actions: list[Id]
    uncertainty: Text
    followups: list[Text]
    insufficient_evidence: bool


class RevisionResult(Contract):
    original_text: Text
    revision: Optional[Text]
    alternatives: list[Text]
    explanation: Text
    evidence: Citations
    assumptions: list[Text]
    decisions: list[Text]
    acceptance_tests: list[Text]
    requires_human_approval: Approval


class Change(Contract):
    kind: Literal[
        "added",
        "removed",
        "changed",
        "contradiction",
        "missing_interface",
        "conflicting_constraint",
        "potentially_resolved",
        "remaining_defect",
        "new_defect",
        "match",
    ]
    alignment: Literal["exact", "semantic", "uncertain"]
    description: Text
    evidence: Citations
    requirement_ids: list[Id]
    related_finding_ids: list[Id]
    uncertainty: Text


class CompareResult(Contract):
    relationship: Literal["complementary", "conflicting", "versions", "uncertain"]
    changes: list[Change]
    questions: list[Text]


class SyntheticDocument(Contract):
    document_id: Id
    blocks: Annotated[list[Block], Field(min_length=1)]


class CaseClassification(Contract):
    document_id: Id
    clean: bool


class ProposedLabel(Contract):
    kind: Id
    explanation: Text
    evidence: Citations


class BenchmarkResult(Contract):
    documents: Annotated[list[SyntheticDocument], Field(min_length=2, max_length=12)]
    case_labels: list[CaseClassification]
    candidate_labels: Annotated[list[ProposedLabel], Field(min_length=1)]
    requires_review: Approval


# Input and output limits include system instructions, schema, and thinking tokens.
# The provider conservatively reserves one input token per UTF-8 byte plus framing.
ROLES = {
    "extract": (ExtractInput, Inventory, "fast", 180000, 8192),
    "individual": (IndividualInput, IndividualResult, "reasoning", 120000, 16384),
    "global": (GlobalInput, GlobalResult, "reasoning", 320000, 16384),
    "critic": (CriticInput, CriticResult, "reasoning", 240000, 16384),
    "risk": (RiskInput, RiskResult, "reasoning", 120000, 8192),
    "copilot": (CopilotInput, CopilotResult, "fast", 100000, 4096),
    "revision": (RevisionInput, RevisionResult, "reasoning", 100000, 8192),
    "compare": (CompareInput, CompareResult, "reasoning", 320000, 16384),
    "benchmark": (BenchmarkInput, BenchmarkResult, "fast", 32000, 8192),
}


def role_catalog():
    """Bundled JSON Schemas and limits for every v1 input/output pair."""
    models = [(cls, "validation") for spec in ROLES.values() for cls in spec[:2]]
    refs, schemas = models_json_schema(models)
    return {
        "version": VERSION,
        "$defs": schemas["$defs"],
        "operations": {
            role: {
                "input": refs[(input_type, "validation")],
                "output": refs[(output_type, "validation")],
                "tier": tier,
                "input_token_upper_limit": input_limit,
                "max_output_tokens": output_limit,
            }
            for role, (input_type, output_type, tier, input_limit, output_limit) in ROLES.items()
        },
    }


def require(condition, code):
    if not condition:
        raise IntelligenceError(code)


def checked(model, data, code):
    try:
        return model.model_validate(data)
    except ValidationError:
        raise IntelligenceError(code) from None


def unique(items, code):
    keys = list(items)
    require(len(keys) == len(set(keys)), code)
    return set(keys)


def coverage(items, expected, code):
    require(unique(items, code) == set(expected), code)


def ref_key(ref):
    return (ref.document_id, ref.block_id)


def block_index(blocks):
    unique((ref_key(block) for block in blocks), "duplicate_block")
    return {ref_key(block): block for block in blocks}


def check_citations(citations, blocks, quotes_only=False):
    for cite in citations:
        block = blocks.get(ref_key(cite))
        require(block is not None, "unknown_source")
        if cite.kind == "quote":
            require(cite.quote and cite.quote in block.text, "quotation_mismatch")
        else:
            require(
                not quotes_only
                and cite.quote is None
                and cite.scope
                and cite.scope in (block.block_id, block.section),
                "invalid_absence_scope",
            )


def check_candidate(item, blocks, requirements):
    require(set(item.requirement_ids) <= requirements, "unknown_requirement")
    check_citations(item.evidence, blocks)
    if item.kind.casefold() in {"contradiction", "conflict", "противоречие"}:
        statements = {(ref_key(c), c.quote) for c in item.evidence if c.kind == "quote"}
        require(len(statements) >= 2 and item.conflict_scenario, "contradiction_incomplete")


def input_context(role, payload):
    require(role in ROLES, "unknown_role")
    obj = checked(ROLES[role][0], payload, "invalid_role_input")
    blocks = block_index(getattr(obj, "blocks", []))
    registry = getattr(obj, "requirements", [])
    ids = unique((r.requirement_id for r in registry), "duplicate_requirement")
    for req in registry:
        check_citations(req.evidence, blocks, quotes_only=True)
    for item in [*getattr(obj, "candidates", []), *getattr(obj, "findings", [])]:
        check_candidate(item, blocks, ids)
    finding_ids = unique((f.finding_id for f in getattr(obj, "findings", [])), "duplicate_finding")
    if role == "extract" and obj.metadata:
        require({doc for doc, _ in blocks} == {obj.metadata.document_id}, "metadata_document_mismatch")
    if role == "individual":
        unique(obj.criteria, "duplicate_criterion")
        require(bool(ids), "empty_requirement_batch")
    if role == "critic":
        unique((c.candidate_id for c in obj.candidates), "duplicate_candidate")
    if role == "copilot":
        require(
            obj.selected_requirement_id is None or obj.selected_requirement_id in ids, "unknown_requirement"
        )
        require(obj.selected_finding_id is None or obj.selected_finding_id in finding_ids, "unknown_finding")
    if role == "revision":
        require(obj.target_requirement_id in ids, "unknown_requirement")
        require(
            any(obj.target_requirement_id in f.requirement_ids for f in obj.findings), "unrelated_finding"
        )
    if role == "compare":
        documents = {doc for doc, _ in blocks}
        coverage(
            [obj.primary_document_id, *obj.supplementary_document_ids], documents, "comparison_document_scope"
        )
    return obj, blocks, ids, finding_ids


def verify(role, payload, output):
    """Validate both dictionaries without network access. Return only schema fields."""
    context, blocks, ids, finding_ids = input_context(role, payload)
    return _verify(role, context, blocks, ids, finding_ids, output)


def _verify(role, context, blocks, ids, finding_ids, output):
    result = checked(ROLES[role][1], output, "invalid_role_output")
    if role == "extract":
        covered = {ref_key(r) for r in result.unclassified}
        require(covered <= set(blocks), "unknown_source")
        explicit = set(context.existing_ids)
        for req in result.requirements:
            check_citations(req.evidence, blocks, quotes_only=True)
            require(len({c.document_id for c in req.evidence}) == 1, "mixed_document_requirement")
            if req.section:
                require(
                    any(req.section == blocks[ref_key(c)].section for c in req.evidence), "unknown_section"
                )
            if req.original_id:
                pattern = r"(?<!\w)" + re.escape(req.original_id) + r"(?!\w)"
                require(
                    any(re.search(pattern, blocks[ref_key(c)].text) for c in req.evidence),
                    "unknown_original_id",
                )
                explicit.add(req.original_id)
            covered.update(ref_key(c) for c in req.evidence)
        for req in result.requirements:
            require(set(req.relationships) <= explicit, "unknown_relationship")
        require(covered == set(blocks), "incomplete_source_coverage")
    elif role == "individual":
        coverage((a.requirement_id for a in result.assessments), ids, "incomplete_assessment")
        for row in result.assessments:
            coverage((a.criterion for a in row.criteria), context.criteria, "incomplete_criteria")
            for item in row.findings:
                check_candidate(item, blocks, ids)
                require(row.requirement_id in item.requirement_ids, "unrelated_finding")
    elif role == "global":
        for item in result.findings:
            check_candidate(item, blocks, ids)
    elif role == "critic":
        candidates = {c.candidate_id for c in context.candidates}
        coverage((v.candidate_id for v in result.verdicts), candidates, "incomplete_verdicts")
        reviewed = {}
        for verdict in result.verdicts:
            check_citations(verdict.evidence + verdict.counterevidence, blocks)
            require(verdict.verdict != "confirmed" or verdict.evidence, "missing_support")
            if verdict.verdict == "duplicate":
                require(
                    reviewed.get(verdict.duplicate_of) in ("confirmed", "requires_clarification"),
                    "invalid_duplicate",
                )
            else:
                require(verdict.duplicate_of is None, "invalid_duplicate")
            reviewed[verdict.candidate_id] = verdict.verdict
    elif role == "risk":
        coverage((r.finding_id for r in result.risks), finding_ids, "incomplete_risks")
        finding_sources = {f.finding_id: {ref_key(c) for c in f.evidence} for f in context.findings}
        for risk in result.risks:
            check_citations(risk.evidence, blocks)
            require(
                any(ref_key(c) in finding_sources[risk.finding_id] for c in risk.evidence), "unrelated_risk"
            )
    elif role == "copilot":
        check_citations(result.evidence, blocks)
        require(result.evidence or result.insufficient_evidence, "missing_support")
        require(set(result.related_finding_ids) <= finding_ids, "unknown_finding")
        require(set(result.actions) <= set(context.supported_actions), "unknown_action")
    elif role == "revision":
        check_citations(result.evidence, blocks)
        req = next(r for r in context.requirements if r.requirement_id == context.target_requirement_id)
        require(any(result.original_text == c.quote for c in req.evidence), "original_text_mismatch")
        require(result.revision or result.alternatives or result.decisions, "empty_revision")
        require(set(result.assumptions) <= set(context.approved_assumptions), "unapproved_assumption")
    elif role == "compare":
        for change in result.changes:
            check_citations(change.evidence, blocks)
            require(set(change.requirement_ids) <= ids, "unknown_requirement")
            require(set(change.related_finding_ids) <= finding_ids, "unknown_finding")
            if change.kind in {"changed", "contradiction", "conflicting_constraint", "match"}:
                quoted = {c.document_id for c in change.evidence if c.kind == "quote" and c.quote}
                require(
                    context.primary_document_id in quoted
                    and quoted.intersection(context.supplementary_document_ids),
                    "missing_comparison_source",
                )
            if change.alignment == "exact" and change.kind == "match":
                quotes = [c.quote for c in change.evidence]
                require(quotes[0] is not None and len(set(quotes)) == 1, "inexact_match")
    else:
        doc_ids = unique((d.document_id for d in result.documents), "duplicate_document")
        coverage((c.document_id for c in result.case_labels), doc_ids, "incomplete_case_labels")
        require(
            len(result.documents) == context.cases and {d.clean for d in result.case_labels} == {True, False},
            "incomplete_benchmark",
        )
        synthetic = block_index([b for d in result.documents for b in d.blocks])
        defective = {d.document_id for d in result.case_labels if not d.clean}
        for d in result.documents:
            require(all(b.document_id == d.document_id for b in d.blocks), "unknown_source")
        labeled = set()
        for label in result.candidate_labels:
            check_citations(label.evidence, synthetic)
            scope = {c.document_id for c in label.evidence} & defective
            require(scope, "label_on_clean_document")
            labeled.update(scope)
        require(defective == labeled, "unlabeled_defect")
    return result.model_dump()


class Intelligence:
    """One bounded run. All instances share the provider's persistent budget."""

    def __init__(self, live=False):
        self.provider = DeepSeek(live=live)
        self.records = self.provider.records

    def run(self, role, payload):
        context, blocks, ids, finding_ids = input_context(role, payload)
        _, output_type, tier, max_input, max_output = ROLES[role]
        if role == "copilot" and context.complex:
            tier = "reasoning"
        system = (
            (PROMPTS / "shared.md").read_text(encoding="utf-8")
            + "\n"
            + (PROMPTS / (role + ".md")).read_text(encoding="utf-8")
        )
        schema = json.dumps(output_type.model_json_schema(), ensure_ascii=False, separators=(",", ":"))
        system += "\nReturn JSON conforming to this output schema:\n" + schema
        if hasattr(context, "requirements"):
            system += (
                "\nFor requirement_id and requirement_ids use only the provided internal registry IDs. "
                "An empty registry permits only empty requirement_ids. Never substitute an original_id. "
                "Copy exact contiguous quotes without normalizing punctuation or Markdown. "
                "Keep criterion explanations concise and specific. For contradiction or conflict "
                "include two distinct source quotations and a concrete conflict_scenario."
            )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": context.model_dump_json(exclude_unset=False)},
        ]
        return self.provider.complete(
            role,
            VERSION,
            tier,
            max_input,
            max_output,
            messages,
            lambda obj: _verify(role, context, blocks, ids, finding_ids, obj),
        )
