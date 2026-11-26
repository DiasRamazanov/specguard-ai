import type { AuditResult, Finding, Requirement, SourceLocation } from '../api/types'

export type View = 'overview' | 'requirements' | 'findings' | 'contradictions' | 'report'

export interface CopilotContext {
  requirement?: Requirement
  finding?: Finding
}

export interface WorkspaceProps {
  result: AuditResult
  filenames: Record<string, string>
  openSource: (loc: SourceLocation, quote?: string | null) => void
  askSpec: (ctx: CopilotContext) => void
  requestRevision: (finding: Finding, requirementId: string) => void
  navigate: (view: View, id?: string) => void
}

export function requirementLabel(r: Requirement): string {
  return r.original_id ?? r.requirement_id
}

export function requirementsById(result: AuditResult): Record<string, Requirement> {
  return Object.fromEntries(result.requirements.map((r) => [r.requirement_id, r]))
}

export function findingsById(result: AuditResult): Record<string, Finding> {
  return Object.fromEntries(result.findings.map((f) => [f.finding_id, f]))
}

const severityRank = { critical: 0, major: 1, minor: 2, informational: 3 } as const
export const bySeverity = (a: Finding, b: Finding) => severityRank[a.severity] - severityRank[b.severity]
