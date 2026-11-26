// Aliases over the generated contract (contracts/openapi.json → schema.d.ts).
// Regenerate with `npm run gen:api`; never hand-edit the shapes here.
import type { components } from './schema'

type S = components['schemas']
export type SessionTicket = S['SessionTicket']
export type DocumentMetadata = S['DocumentMetadata']
export type AuditRequest = S['AuditRequest']
export type AuditStatus = S['AuditStatus']
export type AuditEvent = S['Event']
export type EventStage = AuditEvent['stage']
export type AuditResult = S['AuditResult']
export type Requirement = S['Requirement']
export type RequirementAssessment = S['RequirementAssessment']
export type Finding = S['Finding']
export type Evidence = S['Evidence']
export type SourceBlock = S['SourceBlock']
export type SourceLocation = S['SourceLocation']
export type Attachment = S['Attachment']
export type AttachmentPurpose = Attachment['purpose']
export type CopilotRequest = S['CopilotRequest']
export type CopilotResponse = S['CopilotResponse']
export type RevisionRequest = S['RevisionRequest']
export type RevisionDraft = S['RevisionDraft']
export type ComparisonRequest = S['ComparisonRequest']
export type ComparisonResult = S['ComparisonResult']
export type Readiness = S['Readiness']
export type Severity = Finding['severity']
export type AnalysisMode = NonNullable<AuditRequest['mode']>
