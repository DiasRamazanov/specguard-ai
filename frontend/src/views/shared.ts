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

const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/**
 * Summary for display: drops a leading list marker and a repeated "ID:" prefix. Source text is unchanged.
 * The ID is stripped only when the complete ID is followed by a delimiter (":" "—" "–", or a spaced "-"),
 * so "REQ-1" never matches the start of "REQ-10" or "REQ-1-A".
 */
export function displaySummary(r: Requirement): string {
  let s = r.summary.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, '')
  if (r.original_id) {
    const prefix = new RegExp(`^${escapeRegExp(r.original_id)}(?:\\s*[:—–]|\\s+-)\\s*`)
    const rest = s.replace(prefix, '')
    if (rest !== s && rest.trim()) s = rest
  }
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
