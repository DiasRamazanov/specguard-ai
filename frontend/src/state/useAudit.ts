// Audit lifecycle against the real REST contract: session → upload → audit → poll → result.
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, UPLOAD_LIMIT_BYTES, isAcceptedFile, type SpecGuardClient } from '../api/client'
import type { AnalysisMode, AuditEvent, AuditResult, AuditStatus, DocumentMetadata } from '../api/types'

export type UploadState = 'uploading' | 'ready' | 'error'

export interface LocalDocument {
  localId: string
  file: File
  state: UploadState
  meta?: DocumentMetadata
  error?: string
}

export type Phase = 'setup' | 'running' | 'ready' | 'failed'

export interface AuditController {
  phase: Phase
  documents: LocalDocument[]
  mode: AnalysisMode
  consent: boolean
  auditId: string | null
  status: AuditStatus | null
  result: AuditResult | null
  error: string | null
  setMode: (m: AnalysisMode) => void
  setConsent: (v: boolean) => void
  addFiles: (files: FileList | File[]) => void
  removeDocument: (localId: string) => void
  retryDocument: (localId: string) => void
  start: () => Promise<void>
  newAudit: () => void
  /** Explicit revalidation: audits a new revision as a separate audit; the original is untouched. */
  revalidate: (file: File) => Promise<void>
  refreshEvents: () => Promise<void>
}

let seq = 0
const localId = () => `local-${Date.now().toString(36)}-${(seq++).toString(36)}`

export function validateFile(file: File): string | null {
  if (!isAcceptedFile(file.name)) return 'Поддерживаются файлы PDF, Markdown и TXT.'
  if (file.size === 0) return 'Файл пустой.'
  if (file.size > UPLOAD_LIMIT_BYTES) return 'Файл больше 5 МБ — сервер его не примет.'
  return null
}

export function useAudit(
  client: SpecGuardClient,
  hooks: { onEvents: (auditId: string, events: AuditEvent[]) => void; onError: (message: string) => void; onSession?: () => void },
  pollMs = 450,
): AuditController {
  const [documents, setDocuments] = useState<LocalDocument[]>([])
  const [mode, setMode] = useState<AnalysisMode>('offline')
  const [consent, setConsent] = useState(false)
  const [auditId, setAuditId] = useState<string | null>(null)
  const [status, setStatus] = useState<AuditStatus | null>(null)
  const [result, setResult] = useState<AuditResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [phase, setPhase] = useState<Phase>('setup')
  const hooksRef = useRef(hooks)
  hooksRef.current = hooks
  const generation = useRef(0)

  const docsRef = useRef<LocalDocument[]>([])
  const commit = useCallback((next: LocalDocument[]) => {
    docsRef.current = next
    setDocuments(next)
  }, [])

  const commitRef = useRef(commit)
  commitRef.current = commit

  const fail = useCallback((err: unknown) => {
    const message = err instanceof ApiError ? err.detail : 'Непредвиденная ошибка интерфейса.'
    setError(message)
    hooksRef.current.onError(message)
    return message
  }, [])

  const ensureSession = useCallback(async () => {
    if (await client.ensureSession()) hooksRef.current.onSession?.()
  }, [client])

  const upload = useCallback(
    async (doc: LocalDocument) => {
      const gen = generation.current
      try {
        await ensureSession()
        const meta = await client.uploadDocument(doc.file, doc.file.name)
        if (gen !== generation.current) return
        commitRef.current(docsRef.current.map((d) => (d.localId === doc.localId ? { ...d, state: 'ready', meta, error: undefined } : d)))
      } catch (err) {
        if (gen !== generation.current) return
        const message = err instanceof ApiError ? err.detail : 'Не удалось загрузить файл.'
        commitRef.current(docsRef.current.map((d) => (d.localId === doc.localId ? { ...d, state: 'error', error: message } : d)))
        hooksRef.current.onError(message)
      }
    },
    [client, ensureSession],
  )

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const next = [...docsRef.current]
      const added: LocalDocument[] = []
      for (const file of Array.from(files)) {
        if (next.some((d) => d.file.name === file.name && d.file.size === file.size)) continue
        const problem = validateFile(file)
        const doc: LocalDocument = { localId: localId(), file, state: problem ? 'error' : 'uploading', error: problem ?? undefined }
        next.push(doc)
        if (!problem) added.push(doc)
      }
      commit(next)
      added.forEach((d) => void upload(d))
    },
    [commit, upload],
  )

  const removeDocument = useCallback(
    (id: string) => {
      // The API has no document DELETE; a removed document is simply not sent to the audit.
      commit(docsRef.current.filter((d) => d.localId !== id))
    },
    [commit],
  )

  const retryDocument = useCallback(
    (id: string) => {
      const doc = docsRef.current.find((d) => d.localId === id)
      if (!doc || validateFile(doc.file)) return
      commit(docsRef.current.map((d) => (d.localId === id ? { ...d, state: 'uploading', error: undefined } : d)))
      void upload(doc)
    },
    [commit, upload],
  )

  const start = useCallback(async () => {
    const ids = documents.filter((d) => d.state === 'ready' && d.meta).map((d) => d.meta!.document_id)
    if (!ids.length) return
    setError(null)
    try {
      await ensureSession()
      const st = await client.startAudit({
        document_ids: ids,
        mode,
        allow_external_processing: mode === 'live' ? consent : false,
      })
      setAuditId(st.audit_id)
      setStatus(st)
      setResult(null)
      setPhase('running')
      hooksRef.current.onEvents(st.audit_id, st.events)
    } catch (err) {
      fail(err)
    }
  }, [client, consent, documents, ensureSession, fail, mode])

  // Poll while the job is queued or running.
  useEffect(() => {
    if (phase !== 'running' || !auditId) return
    let alive = true
    let handle: ReturnType<typeof setTimeout>
    const tick = async () => {
      try {
        const st = await client.auditStatus(auditId)
        if (!alive) return
        setStatus(st)
        hooksRef.current.onEvents(auditId, st.events)
        if (st.status === 'completed') {
          const res = await client.auditResult(auditId)
          if (!alive) return
          setResult(res)
          setPhase('ready')
          return
        }
        if (st.status === 'failed') {
          setError(st.error ?? 'Аудит завершился ошибкой.')
          setPhase('failed')
          return
        }
      } catch (err) {
        if (!alive) return
        fail(err)
        setPhase('failed')
        return
      }
      handle = setTimeout(tick, pollMs)
    }
    handle = setTimeout(tick, pollMs)
    return () => {
      alive = false
      clearTimeout(handle)
    }
  }, [auditId, client, fail, phase, pollMs])

  const revalidate = useCallback(
    async (file: File) => {
      const problem = validateFile(file)
      if (problem) {
        hooksRef.current.onError(problem)
        return
      }
      generation.current++
      const doc: LocalDocument = { localId: localId(), file, state: 'uploading' }
      commit([doc])
      setError(null)
      try {
        await ensureSession()
        const meta = await client.uploadDocument(file, file.name)
        commit([{ ...doc, state: 'ready', meta }])
        const st = await client.startAudit({
          document_ids: [meta.document_id],
          mode,
          allow_external_processing: mode === 'live' ? consent : false,
        })
        setAuditId(st.audit_id)
        setStatus(st)
        setResult(null)
        setPhase('running')
        hooksRef.current.onEvents(st.audit_id, st.events)
      } catch (err) {
        fail(err)
        setPhase('setup')
      }
    },
    [client, commit, consent, ensureSession, fail, mode],
  )

  const refreshEvents = useCallback(async () => {
    if (!auditId) return
    try {
      const st = await client.auditStatus(auditId)
      setStatus(st)
      hooksRef.current.onEvents(auditId, st.events)
    } catch {
      /* status refresh is best-effort; the originating action reports its own error */
    }
  }, [auditId, client])

  const newAudit = useCallback(() => {
    // A new audit gets a fresh session so documents, attachments and chat stay isolated.
    generation.current++
    client.resetSession()
    commit([])
    setAuditId(null)
    setStatus(null)
    setResult(null)
    setError(null)
    setPhase('setup')
    setConsent(false)
  }, [client, commit])

  return {
    phase,
    documents,
    mode,
    consent,
    auditId,
    status,
    result,
    error,
    setMode,
    setConsent,
    addFiles,
    removeDocument,
    retryDocument,
    start,
    newAudit,
    revalidate,
    refreshEvents,
  }
}
