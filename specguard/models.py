"""Canonical audit and source records shared by the CLI and API."""

from datetime import datetime
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceLocation(Record):
    document_id: str
    block_id: str
    section: Optional[str] = None
    page: Optional[int] = Field(default=None, ge=1)
    line_start: Optional[int] = Field(default=None, ge=1)
    line_end: Optional[int] = Field(default=None, ge=1)
    char_start: Optional[int] = Field(default=None, ge=0)
    char_end: Optional[int] = Field(default=None, ge=0)
    bbox: Optional[Tuple[float, float, float, float]] = None


class SourceBlock(Record):
    block_id: str
    text: str
    kind: Literal["heading", "paragraph", "list_item", "table_row", "table_header", "code"]
    location: SourceLocation

    @property
    def section(self) -> Optional[str]:
        return self.location.section


class DocumentMetadata(Record):
    document_id: str
    filename: str
    format: Literal["markdown", "pdf", "text"]
    sha256: str
    size_bytes: int
    page_count: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)


class SourceDocument(DocumentMetadata):
    original_text: str
    blocks: List[SourceBlock]


class Evidence(Record):
    evidence_id: str
    kind: Literal["quote", "absence"]
    location: SourceLocation
    quote: Optional[str] = None
    scope: Optional[str] = None


class Requirement(Record):
    requirement_id: str
    document_id: str
    original_id: Optional[str] = None
    summary: str
    kind: str
    section: Optional[str] = None
    evidence: List[Evidence] = Field(min_length=1)
    relationships: List[str] = Field(default_factory=list)
    uncertainty: Optional[str] = None


Severity = Literal["critical", "major", "minor", "informational"]
FindingStatus = Literal["confirmed", "requires_clarification", "context_dependent"]
FindingScope = Literal["individual", "global"]


class Finding(Record):
    finding_id: str
    kind: str
    scope: FindingScope
    title: str
    explanation: str
    criterion: str
    severity: Severity
    status: FindingStatus
    document_ids: List[str] = Field(min_length=1)
    requirement_ids: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(min_length=1)
    impact: str
    recommendation: str
    uncertainty: Optional[str] = None
    conflict_scenario: Optional[str] = None


class RejectedCandidate(Record):
    candidate_id: str
    kind: str
    title: str
    reason: str
    status: Literal["unsupported", "duplicate", "rejected"]


CriterionStatus = Literal[
    "valid",
    "confirmed_defect",
    "requires_clarification",
    "context_dependent",
    "insufficient_evidence",
    "not_applicable",
]


class CriterionAssessment(Record):
    criterion: str
    status: CriterionStatus
    explanation: str


class RequirementAssessment(Record):
    requirement_id: str
    status: Literal["complete", "incomplete", "offline"]
    criteria: List[CriterionAssessment] = Field(default_factory=list)
    finding_ids: List[str] = Field(default_factory=list)
    uncertainty: Optional[str] = None


class AuditCoverage(Record):
    source_blocks: int
    extraction_blocks_reviewed: int
    requirements: int
    individually_assessed: int
    global_pass_complete: bool
    critic_complete: bool
    complete: bool


class Readiness(Record):
    verdict: Literal["ready", "ready_with_conditions", "requires_revision", "unable_to_determine"]
    rationale: str
    confirmed_by_severity: Dict[Severity, int]
    clarification_count: int
    priority_finding_ids: List[str]


class UsageRecord(Record):
    role: str
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    input_tokens: int = 0
    reasoning_tokens: int = 0
    output_tokens: int = 0
    latency_ms: Optional[int] = None
    status: Optional[str] = None


class AuditResult(Record):
    audit_id: str
    created_at: datetime
    agent_version: str
    model: str
    mode: Literal["live", "offline"]
    documents: List[DocumentMetadata] = Field(min_length=1)
    requirements: List[Requirement]
    assessments: List[RequirementAssessment]
    findings: List[Finding]
    rejected_candidates: List[RejectedCandidate]
    readiness: Readiness
    coverage: AuditCoverage
    usage: List[UsageRecord] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
