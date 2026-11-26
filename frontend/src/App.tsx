import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type SpecGuardClient } from './api/client'
import type { Finding, SourceLocation } from './api/types'
import { CopilotPanel, type CopilotHandle } from './copilot/CopilotPanel'
import { Icon, type IconName } from './components/Icons'
import { ModeBadge } from './components/ModeBadge'
import { SourceDrawer, type SourceTarget } from './components/SourceDrawer'
import { isContradiction } from './labels'
import { SpecDock } from './mascot/SpecDock'
import { useMascotDriver } from './mascot/useMascotDriver'
import { useAudit } from './state/useAudit'
import { FindingsView } from './views/FindingsView'
import { OverviewView } from './views/OverviewView'
import { ProgressView } from './views/ProgressView'
import { ReportView } from './views/ReportView'
import { RequirementsView } from './views/RequirementsView'
import { SetupView } from './views/SetupView'
import type { CopilotContext, View, WorkspaceProps } from './views/shared'

interface Toast {
  id: number
  text: string
  kind: 'error' | 'info'
}

export function App({ client = api }: { client?: SpecGuardClient }) {
  const mascot = useMascotDriver('greeting')
  const [toasts, setToasts] = useState<Toast[]>([])
  const toast = useCallback((text: string, kind: Toast['kind'] = 'error') => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t.slice(-2), { id, text, kind }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }, [])

  const audit = useAudit(client, {
    onEvents: mascot.pushEvents,
    onError: (message) => {
      mascot.signal('error')
      toast(message)
    },
  })

  const [view, setView] = useState<View>('overview')
  const [selected, setSelected] = useState<string | undefined>()
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [context, setContext] = useState<CopilotContext>({})
  const [source, setSource] = useState<SourceTarget | null>(null)
  const [motion, setMotion] = useState(true)
  const [shell, setShell] = useState<HTMLDivElement | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const copilot = useRef<CopilotHandle>(null)

  const result = audit.result
  useEffect(() => {
    if (result) {
      setView('overview')
      setSelected(undefined)
      setContext({})
    }
  }, [result])

  const filenames = useMemo(
    () => Object.fromEntries((result?.documents ?? []).map((d) => [d.document_id, d.filename])),
    [result],
  )

  const toggleCopilot = useCallback((open: boolean) => {
    setCopilotOpen(open)
    if (!open) trigger.current?.focus()
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && copilotOpen) toggleCopilot(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [copilotOpen, toggleCopilot])

  /** Polls the job's real event list while a Copilot/attachment request runs. */
  const track = useCallback(
    async <T,>(work: Promise<T>, opts?: { settle?: boolean }): Promise<T> => {
      const timer = setInterval(() => void audit.refreshEvents(), 400)
      try {
        return await work
      } finally {
        clearInterval(timer)
        await audit.refreshEvents()
        // The backend reports no "attachment ready" stage; the 201 response with
        // extraction_status="extracted" is the real completion signal.
        if (opts?.settle) mascot.signal('idle')
      }
    },
    [audit, mascot],
  )

  const navigate = useCallback((v: View, id?: string) => {
    setView(v)
    setSelected(id)
  }, [])

  const openSource = useCallback((location: SourceLocation, quote?: string | null) => setSource({ location, quote }), [])

  const askSpec = useCallback((ctx: CopilotContext) => {
    setContext(ctx)
    setCopilotOpen(true)
    setTimeout(() => copilot.current?.focusComposer(), 380)
  }, [])

  const requestRevision = useCallback((finding: Finding, requirementId: string) => {
    setContext({ finding })
    setCopilotOpen(true)
    copilot.current?.requestRevision(finding, requirementId)
  }, [])

  const workspace: WorkspaceProps | null = result ? { result, filenames, openSource, askSpec, requestRevision, navigate } : null

  const nav: { id: View; label: string; icon: IconName; count?: number }[] = [
    { id: 'overview', label: 'Обзор', icon: 'home' },
    { id: 'requirements', label: 'Требования', icon: 'doc', count: result?.requirements.length },
    { id: 'findings', label: 'Замечания', icon: 'alert', count: result?.findings.length },
    { id: 'contradictions', label: 'Противоречия', icon: 'swap', count: result?.findings.filter(isContradiction).length },
    { id: 'report', label: 'Отчёт', icon: 'report' },
  ]

  const docName = result?.documents.map((d) => d.filename).join(', ') ?? audit.documents.map((d) => d.file.name).join(', ')

  return (
    <div className="shell" ref={setShell} data-motion={motion ? 'on' : 'off'}>
      <nav className="sidebar" aria-label="Навигация по аудиту">
        <div className="logo">
          <span className="logo-mark"><Icon name="shield" size={17} /></span>
          <span>SpecGuard <span className="ai">AI</span></span>
        </div>
        <div className="nav">
          {nav.map((n) => (
            <button
              key={n.id}
              type="button"
              className="nav-item"
              aria-current={result && view === n.id ? 'page' : undefined}
              disabled={!result}
              onClick={() => navigate(n.id)}
            >
              <Icon name={n.icon} size={18} />
              {n.label}
              {n.count != null && <span className="count">{n.count}</span>}
            </button>
          ))}
        </div>
        <SpecDock
          ref={trigger}
          state={mascot.state}
          open={copilotOpen}
          onToggle={toggleCopilot}
          gazeRoot={shell}
          motion={motion}
          onMotionChange={setMotion}
        />
      </nav>

      <main className="main">
        <div className="topbar">
          <div className="crumbs">
            <span>Аудиты</span>
            {docName && (
              <>
                <Icon name="chevron" size={14} />
                <b>{docName}</b>
              </>
            )}
          </div>
          <span className="spacer" />
          {(result || audit.phase === 'running') && <ModeBadge mode={result?.mode ?? audit.mode} model={result?.mode === 'live' ? result.model : undefined} />}
          {audit.phase !== 'setup' && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => { audit.newAudit(); mascot.reset(); setCopilotOpen(false) }}>
              <Icon name="plus" size={15} /> Новый анализ
            </button>
          )}
        </div>

        {audit.phase === 'setup' && <SetupView audit={audit} />}
        {(audit.phase === 'running' || audit.phase === 'failed') && <ProgressView audit={audit} />}
        {audit.phase === 'ready' && workspace && (
          <>
            {view === 'overview' && <OverviewView {...workspace} />}
            {view === 'requirements' && <RequirementsView {...workspace} selectedId={selected} />}
            {view === 'findings' && <FindingsView key="f" {...workspace} selectedId={selected} />}
            {view === 'contradictions' && <FindingsView key="c" {...workspace} selectedId={selected} contradictionsOnly />}
            {view === 'report' && <ReportView {...workspace} client={client} />}
          </>
        )}
      </main>

      <div id="spec-copilot">
        <CopilotPanel
          key={result?.audit_id ?? 'none'}
          ref={copilot}
          open={copilotOpen}
          onClose={() => toggleCopilot(false)}
          client={client}
          result={result}
          context={context}
          clearContext={() => setContext({})}
          defaultMode={result?.mode ?? 'offline'}
          filenames={filenames}
          openSource={openSource}
          track={track}
          onError={() => mascot.signal('error')}
          onRevalidate={(file) => {
            if (window.confirm('Новая редакция будет проверена отдельным аудитом. Исходный аудит не изменится. Продолжить?')) {
              setCopilotOpen(false)
              void audit.revalidate(file)
            }
          }}
        />
      </div>

      {source && result && (
        <SourceDrawer client={client} auditId={result.audit_id} target={source} filenames={filenames} onClose={() => setSource(null)} />
      )}

      <div className="toast-stack" aria-live="assertive">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`} role={t.kind === 'error' ? 'alert' : 'status'}>
            {t.text}
          </div>
        ))}
      </div>
    </div>
  )
}
