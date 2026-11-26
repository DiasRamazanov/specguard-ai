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

/** Summary for display: drops a leading list marker and a repeated "ID:" prefix. Source text is unchanged. */
export function displaySummary(r: Requirement): string {
  let s = r.summary.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, '')
  if (r.original_id && s.startsWith(r.original_id)) s = s.slice(r.original_id.length).replace(/^\s*[:—–-]\s*/, '')
  return s || r.summary
}

export const SEVERITY_COLOR = { critical: 'var(--critical)', major: 'var(--warning)', minor: '#eab308', informational: 'var(--info)' } as const

export function requirementsById(result: AuditResult): Record<string, Requirement> {
  return Object.fromEntries(result.requirements.map((r) => [r.requirement_id, r]))
}

export function findingsById(result: AuditResult): Record<string, Finding> {
  return Object.fromEntries(result.findings.map((f) => [f.finding_id, f]))
}

const severityRank = { critical: 0, major: 1, minor: 2, informational: 3 } as const
export const bySeverity = (a: Finding, b: Finding) => severityRank[a.severity] - severityRank[b.severity]
