// Thin, typed client for the SpecGuard REST contract (contracts/openapi.json).
// The session token lives only in memory (docs/architecture.md, step 1).
import type {
  Attachment,
  AttachmentPurpose,
  AuditRequest,
  AuditResult,
  AuditStatus,
  ComparisonRequest,
  ComparisonResult,
  CopilotRequest,
  CopilotResponse,
  DocumentMetadata,
  Finding,
  Requirement,
  RevisionDraft,
  RevisionRequest,
  SessionTicket,
  SourceBlock,
} from './types'

export const API_BASE = '/api'

/** Backend-enforced body limit for uploads (specguard/api.py UPLOAD_LIMIT). Checked early for UX; 413 is still handled. */
export const UPLOAD_LIMIT_BYTES = 5 * 1024 * 1024

/** Formats the backend parses (specguard/ingest.py). DOCX/XLSX are not accepted by the API. */
export const ACCEPTED_EXTENSIONS = ['.pdf', '.md', '.markdown', '.txt'] as const
export const ACCEPT_ATTRIBUTE = ACCEPTED_EXTENSIONS.join(',')

export class ApiError extends Error {
  readonly status: number
  readonly detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function contentTypeFor(filename: string): string {
  const lower = filename.toLowerCase()
  if (lower.endsWith('.pdf')) return 'application/pdf'
  if (lower.endsWith('.md') || lower.endsWith('.markdown')) return 'text/markdown'
  if (lower.endsWith('.txt')) return 'text/plain'
  return 'application/octet-stream'
}

export function isAcceptedFile(name: string): boolean {
  const lower = name.toLowerCase()
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext))
}

type FetchLike = typeof fetch

export class SpecGuardClient {
  private token: string | null = null
  private readonly fetcher: FetchLike

  constructor(fetcher: FetchLike = (...args) => fetch(...args)) {
    this.fetcher = fetcher
  }

  get hasSession(): boolean {
    return this.token !== null
  }

  private async request<T>(path: string, init: RequestInit = {}, expect: 'json' | 'text' | 'none' = 'json'): Promise<T> {
    const headers = new Headers(init.headers)
    if (this.token) headers.set('Authorization', `Bearer ${this.token}`)
    let response: Response
    try {
      response = await this.fetcher(`${API_BASE}${path}`, { ...init, headers })
    } catch {
      throw new ApiError(0, 'Сервер SpecGuard недоступен. Проверьте, что backend запущен.')
    }
    if (!response.ok) {
      let detail = `Ошибка ${response.status}`
      try {
        const body = (await response.json()) as { detail?: unknown }
        if (typeof body.detail === 'string') detail = body.detail
      } catch {
        /* non-JSON error body (e.g. proxy failure) */
        if (response.status >= 500 && response.status !== 503) detail = 'Сервер SpecGuard недоступен или вернул ошибку.'
      }
      throw new ApiError(response.status, detail)
    }
    if (expect === 'none') return undefined as T
    if (expect === 'text') return (await response.text()) as T
    return (await response.json()) as T
  }

  private json<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  private upload<T>(path: string, file: Blob, filename: string): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      headers: { 'Content-Type': contentTypeFor(filename) },
      body: file,
    })
  }

  health(): Promise<{ status: string }> {
    return this.request('/health')
  }

  async createSession(): Promise<SessionTicket> {
    const ticket = await this.request<SessionTicket>('/sessions', { method: 'POST' })
    this.token = ticket.token
    return ticket
  }

  private pendingSession: Promise<SessionTicket> | null = null

  /** Creates a session once, even when several uploads start concurrently. Returns true if a new one was created. */
  async ensureSession(): Promise<boolean> {
    if (this.token) return false
    if (!this.pendingSession) {
      this.pendingSession = this.createSession().finally(() => {
        this.pendingSession = null
      })
      await this.pendingSession
      return true
    }
    await this.pendingSession
    return false
  }

  resetSession(): void {
    this.token = null
    this.pendingSession = null
  }

  uploadDocument(file: Blob, filename: string): Promise<DocumentMetadata> {
    return this.upload(`/documents?filename=${encodeURIComponent(filename)}`, file, filename)
  }

  startAudit(req: AuditRequest): Promise<AuditStatus> {
    return this.json('/audits', req)
  }

  auditStatus(auditId: string): Promise<AuditStatus> {
    return this.request(`/audits/${encodeURIComponent(auditId)}`)
  }

  auditResult(auditId: string): Promise<AuditResult> {
    return this.request(`/audits/${encodeURIComponent(auditId)}/result`)
  }

  requirement(auditId: string, requirementId: string): Promise<Requirement> {
    return this.request(`/audits/${encodeURIComponent(auditId)}/requirements/${encodeURIComponent(requirementId)}`)
  }

  finding(auditId: string, findingId: string): Promise<Finding> {
    return this.request(`/audits/${encodeURIComponent(auditId)}/findings/${encodeURIComponent(findingId)}`)
  }

  source(auditId: string, documentId: string, blockId: string): Promise<SourceBlock> {
    return this.request(
      `/audits/${encodeURIComponent(auditId)}/sources/${encodeURIComponent(documentId)}/${encodeURIComponent(blockId)}`,
    )
  }

  report(auditId: string): Promise<string> {
    return this.request(`/audits/${encodeURIComponent(auditId)}/report`, {}, 'text')
  }

  addAttachment(auditId: string, file: Blob, filename: string, purpose: AttachmentPurpose): Promise<Attachment> {
    const q = `purpose=${encodeURIComponent(purpose)}&filename=${encodeURIComponent(filename)}`
    return this.upload(`/audits/${encodeURIComponent(auditId)}/attachments?${q}`, file, filename)
  }

  listAttachments(auditId: string): Promise<Attachment[]> {
    return this.request(`/audits/${encodeURIComponent(auditId)}/attachments`)
  }

  removeAttachment(auditId: string, attachmentId: string): Promise<void> {
    return this.request(
      `/audits/${encodeURIComponent(auditId)}/attachments/${encodeURIComponent(attachmentId)}`,
      { method: 'DELETE' },
      'none',
    )
  }

  copilot(auditId: string, req: CopilotRequest): Promise<CopilotResponse> {
    return this.json(`/audits/${encodeURIComponent(auditId)}/copilot`, req)
  }

  revision(auditId: string, req: RevisionRequest): Promise<RevisionDraft> {
    return this.json(`/audits/${encodeURIComponent(auditId)}/revisions`, req)
  }

  compare(auditId: string, req: ComparisonRequest): Promise<ComparisonResult> {
    return this.json(`/audits/${encodeURIComponent(auditId)}/comparisons`, req)
  }
}

export const api = new SpecGuardClient()
