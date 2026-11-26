"""Wire types for sessions, progress polling and evidence navigation."""

from datetime import datetime
from typing import Literal

from pydantic import Field, StrictBool

from .models import DocumentMetadata, Evidence, Record

Mode = Literal["offline", "live"]
Purpose = Literal["context", "comparison", "revision"]
Stage = Literal[
    "document_received",
    "extracting",
    "validating_individual",
    "validating_global",
    "contradiction_detected",
    "verifying_evidence",
    "generating_report",
    "completed",
    "failed",
    "attachment_received",
    "attachment_reading",
    "comparing_documents",
    "copilot_thinking",
    "copilot_response_completed",
]


class ErrorResponse(Record):
    detail: str


class SessionTicket(Record):
    token: str
    ttl_seconds: int


class AuditRequest(Record):
    document_ids: list[str] = Field(min_length=1, max_length=4)
    mode: Mode = "offline"
    allow_external_processing: StrictBool = False


class Event(Record):
    sequence: int
    stage: Stage
    time: datetime
    finding_id: str | None = None


class AuditStatus(Record):
    audit_id: str
    status: Literal["queued", "running", "completed", "failed"]
    events: list[Event]
    error: str | None = None


class Attachment(Record):
    attachment_id: str
    document: DocumentMetadata
    purpose: Purpose
    extraction_status: Literal["extracted"] = "extracted"


class CopilotRequest(Record):
    question: str = Field(min_length=1, max_length=4000)
    requirement_id: str | None = None
    finding_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=4)
    mode: Mode = "offline"
    allow_external_processing: StrictBool = False


class CopilotResponse(Record):
    answer: str
    evidence: list[Evidence]
    related_finding_ids: list[str]
    clarification_questions: list[str]
    proposed_actions: list[str]
    uncertainty: str | None = None


class RevisionRequest(Record):
    requirement_id: str
    finding_id: str
    approved_assumptions: list[str] = Field(default_factory=list, max_length=12)
    allow_external_processing: StrictBool = False


class RevisionDraft(Record):
    original_text: str
    proposed_revision: str | None
    alternatives: list[str]
    explanation: str
    evidence: list[Evidence]
    assumptions: list[str]
    decisions: list[str]
    acceptance_tests: list[str]
    requires_human_approval: Literal[True]


class ComparisonRequest(Record):
    primary_document_id: str
    attachment_ids: list[str] = Field(min_length=1, max_length=4)
    purpose: str = Field(min_length=1, max_length=1000)
    allow_external_processing: StrictBool = False


class ComparisonChange(Record):
    kind: str
    alignment: str
    description: str
    evidence: list[Evidence]
    requirement_ids: list[str]
    related_finding_ids: list[str]
    uncertainty: str


class ComparisonResult(Record):
    relationship: str
    changes: list[ComparisonChange]
    questions: list[str]
