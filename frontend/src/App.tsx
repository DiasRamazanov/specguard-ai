import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, type SpecGuardClient } from './api/client'
import type { Finding, SourceLocation } from './api/types'
import { CopilotPanel, type CopilotHandle } from './copilot/CopilotPanel'
import { BrandMark } from './components/BrandMark'
import { ConfirmDialog } from './components/ConfirmDialog'
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

const VIEWS: View[] = ['overview', 'requirements', 'findings', 'contradictions', 'report']
const VIEW_TITLES: Record<View, string> = {
  overview: 'Обзор',
  requirements: 'Требования',
  findings: 'Замечания',
  contradictions: 'Противоречия',
  report: 'Отчёт',
}

/** Deep links: #/<view>[/<id>] — lets the browser Back button move between views. */
export function parseRoute(hash: string): { view: View; id?: string } | null {
  const m = /^#\/([a-z]+)(?:\/(.+))?$/.exec(hash)
  if (!m || !VIEWS.includes(m[1] as View)) return null
  return { view: m[1] as View, id: m[2] ? decodeURIComponent(m[2]) : undefined }
}
export const routeHash = (view: View, id?: string) => `#/${view}${id ? `/${encodeURIComponent(id)}` : ''}`

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
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 7000)
  }, [])
  const dismissToast = (id: number) => setToasts((t) => t.filter((x) => x.id !== id))

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
  const [pendingRevalidation, setPendingRevalidation] = useState<File | null>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const main = useRef<HTMLElement>(null)
  const copilot = useRef<CopilotHandle>(null)

  const result = audit.result
  useEffect(() => {
    if (result) {
      setView('overview')
      setSelected(undefined)
      setContext({})
      history.replaceState(null, '', routeHash('overview'))
    }
  }, [result])

  // Browser Back/Forward between views of the current audit.
  useEffect(() => {
    const onPop = () => {
      if (!result) return
      const route = parseRoute(location.hash) ?? { view: 'overview' as View }
      setView(route.view)
      setSelected(route.id)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [result])

  // Descriptive tab title per screen.
  useEffect(() => {
    const base = 'SpecGuard AI'
    document.title =
      audit.phase === 'ready'
        ? `${VIEW_TITLES[view]} · ${base}`
        : audit.phase === 'running'
          ? `Анализ… · ${base}`
          : audit.phase === 'failed'
            ? `Ошибка анализа · ${base}`
            : `${base} — аудит технических заданий`
  }, [audit.phase, view])

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
    const hash = routeHash(v, id)
    if (location.hash !== hash) history.pushState(null, '', hash)
  }, [])

  /** Sidebar navigation also moves focus to the new content for keyboard and screen-reader users. */
  const navigateFromMenu = (v: View) => {
    navigate(v)
    requestAnimationFrame(() => {
      const heading = main.current?.querySelector<HTMLElement>('h1')
      if (!heading) return
      heading.tabIndex = -1
      heading.focus({ preventScroll: true })
    })
  }

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
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); main.current?.focus() }}>
        Перейти к содержимому
      </a>
      <nav className="sidebar" aria-label="Навигация по аудиту">
        <div className="logo">
          <BrandMark />
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
              title={result ? undefined : 'Доступно после завершения анализа'}
              onClick={() => navigateFromMenu(n.id)}
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

      <main className="main" id="main" ref={main} tabIndex={-1}>
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
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => { audit.newAudit(); mascot.reset(); setCopilotOpen(false); history.replaceState(null, '', location.pathname + location.search) }}>
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
          onRevalidate={(file) => setPendingRevalidation(file)}
        />
      </div>

      {source && result && (
        <SourceDrawer client={client} auditId={result.audit_id} target={source} filenames={filenames} onClose={() => setSource(null)} />
      )}

      {pendingRevalidation && (
        <ConfirmDialog
          title="Перепроверить новую редакцию?"
          confirmLabel="Запустить отдельный аудит"
          onCancel={() => setPendingRevalidation(null)}
          onConfirm={() => {
            const file = pendingRevalidation
            setPendingRevalidation(null)
            setCopilotOpen(false)
            void audit.revalidate(file)
          }}
        >
          Файл «{pendingRevalidation.name}» будет проверен отдельным аудитом. Текущий аудит и его результаты не изменятся.
        </ConfirmDialog>
      )}

      <div className="toast-stack" aria-live="assertive">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`} role={t.kind === 'error' ? 'alert' : 'status'}>
            <span style={{ flex: 1 }}>{t.text}</span>
            <button type="button" className="icon-btn" onClick={() => dismissToast(t.id)} aria-label="Закрыть уведомление">
              <Icon name="x" size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
