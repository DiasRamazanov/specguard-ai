// SPEC Copilot: right-side panel (SPEC 4.2). Evidence-grounded answers from
// POST /audits/{id}/copilot, approval-only revision drafts, document comparison and
// multi-file attachments. Nothing here alters the original audit.
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { ACCEPT_ATTRIBUTE, ApiError, type SpecGuardClient } from '../api/client'
import type {
  AnalysisMode,
  AttachmentPurpose,
  AuditResult,
  ComparisonResult,
  CopilotResponse,
  Finding,
  RevisionDraft,
  SourceLocation,
} from '../api/types'
import { EvidenceList } from '../components/Evidence'
import { Icon } from '../components/Icons'
import { SpecMascot } from '../mascot/SpecMascot'
import { PURPOSE_LABELS, VERDICT_LABELS, fileTypeLabel, formatBytes } from '../labels'
import { requirementLabel, type CopilotContext } from '../views/shared'
import { useAttachments, type AttachmentChip } from './useAttachments'
import './copilot.css'

type DistributiveOmit<T, K extends keyof never> = T extends unknown ? Omit<T, K> : never

type Message =
  | { id: number; role: 'user'; text: string; files: string[]; context?: string }
  | { id: number; role: 'answer'; response: CopilotResponse; mode: AnalysisMode }
  | { id: number; role: 'draft'; draft: RevisionDraft; findingTitle: string; requirement: string; decision: 'pending' | 'approved' | 'rejected' }
  | { id: number; role: 'comparison'; result: ComparisonResult }
  | { id: number; role: 'error'; text: string }

export interface CopilotHandle {
  requestRevision: (finding: Finding, requirementId: string) => void
  focusComposer: () => void
}

interface Props {
  open: boolean
  onClose: () => void
  client: SpecGuardClient
  result: AuditResult | null
  context: CopilotContext
  clearContext: () => void
  defaultMode: AnalysisMode
  filenames: Record<string, string>
  openSource: (loc: SourceLocation, quote?: string | null) => void
  /** Wraps a backend call so App can surface the job's real events on SPEC while it runs. */
  track: <T>(work: Promise<T>, opts?: { settle?: boolean }) => Promise<T>
  onError: (message: string) => void
  onRevalidate: (file: File) => void
}

const SUGGESTIONS = ['Почему ТЗ не готово к разработке?', 'Что исправить в первую очередь?', 'Сравнить два технических задания']

let mid = 0
const nextId = () => ++mid

export const CopilotPanel = forwardRef<CopilotHandle, Props>(function CopilotPanel(props, ref) {
  const { open, onClose, client, result, context, clearContext, defaultMode, filenames, openSource, track, onError, onRevalidate } = props
  const auditId = result?.audit_id ?? null
  const [messages, setMessages] = useState<Message[]>([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [purpose, setPurpose] = useState<AttachmentPurpose>('context')
  const [mode, setMode] = useState<AnalysisMode>(defaultMode)
  const [consent, setConsent] = useState(false)
  const [dragging, setDragging] = useState(false)
  const textarea = useRef<HTMLTextAreaElement>(null)
  const picker = useRef<HTMLInputElement>(null)
  const closeBtn = useRef<HTMLButtonElement>(null)
  const history = useRef<HTMLDivElement>(null)
  const att = useAttachments(client, auditId, { onChange: (ok) => void track(Promise.resolve(), { settle: ok }), onError })

  const push = (m: DistributiveOmit<Message, 'id'>) => setMessages((ms) => [...ms, { ...m, id: nextId() } as Message])
  const live = mode === 'live'
  const allowExternal = live && consent

  useEffect(() => {
    if (open) closeBtn.current?.focus()
  }, [open])

  useEffect(() => {
    history.current?.lastElementChild?.scrollIntoView({ block: 'nearest' })
  }, [messages])

  const failMessage = (err: unknown) => {
    const message = err instanceof ApiError ? err.detail : 'Запрос не выполнен.'
    push({ role: 'error', text: message })
    onError(message)
  }

  const ready = (c: AttachmentChip) => c.state === 'extracted' && c.attachment
  const selectedIds = att.chips.filter((c) => c.selected && ready(c)).map((c) => c.attachment!.attachment_id)

  const ask = async (question: string) => {
    if (!auditId || busy) return
    const q = question.trim() || 'Проанализируй вложения'
    const files = att.chips.filter((c) => c.selected && ready(c)).map((c) => c.file.name)
    push({
      role: 'user',
      text: q,
      files,
      context: context.finding ? context.finding.title : context.requirement ? requirementLabel(context.requirement) : undefined,
    })
    setText('')
    setBusy(true)
    try {
      const response = await track(
        client.copilot(auditId, {
          question: q.slice(0, 4000),
          requirement_id: context.requirement?.requirement_id ?? null,
          finding_id: context.finding?.finding_id ?? null,
          attachment_ids: selectedIds,
          mode,
          allow_external_processing: allowExternal,
        }),
      )
      push({ role: 'answer', response, mode })
    } catch (err) {
      failMessage(err)
    } finally {
      setBusy(false)
    }
  }

  const liveOnly = (what: string) => {
    push({
      role: 'error',
      text: `${what} выполняет модель DeepSeek. Переключите режим внизу панели на «DeepSeek» и подтвердите согласие на отправку текста. В офлайн-режиме доступны поиск по источникам и навигация по замечаниям.`,
    })
  }

  const compare = async () => {
    if (!auditId || !result || busy) return
    if (!allowExternal) return liveOnly('Сравнение документов')
    const ids = att.chips
      .filter((c) => c.selected && ready(c) && (c.purpose === 'comparison' || c.purpose === 'revision'))
      .map((c) => c.attachment!.attachment_id)
    if (!ids.length) return
    const purposeText = text.trim() || 'Сравнить редакции и выявить изменения требований'
    push({ role: 'user', text: `Сравнение: ${purposeText}`, files: att.chips.filter((c) => ids.includes(c.attachment?.attachment_id ?? '')).map((c) => c.file.name) })
    setText('')
    setBusy(true)
    try {
      const res = await track(
        client.compare(auditId, {
          primary_document_id: result.documents[0].document_id,
          attachment_ids: ids,
          purpose: purposeText.slice(0, 1000),
          allow_external_processing: allowExternal,
        }),
      )
      push({ role: 'comparison', result: res })
    } catch (err) {
      failMessage(err)
    } finally {
      setBusy(false)
    }
  }

  const requestRevision = async (finding: Finding, requirementId: string) => {
    if (!auditId || !result) return
    const req = result.requirements.find((r) => r.requirement_id === requirementId)
    const reqLabel = req ? requirementLabel(req) : requirementId
    push({ role: 'user', text: `Предложи исправление ${reqLabel} по замечанию «${finding.title}»`, files: [] })
    if (!allowExternal) return liveOnly('Черновик исправления')
    setBusy(true)
    try {
      const draft = await track(
        client.revision(auditId, {
          requirement_id: requirementId,
          finding_id: finding.finding_id,
          approved_assumptions: [],
          allow_external_processing: allowExternal,
        }),
      )
      push({ role: 'draft', draft, findingTitle: finding.title, requirement: reqLabel, decision: 'pending' })
    } catch (err) {
      failMessage(err)
    } finally {
      setBusy(false)
    }
  }

  useImperativeHandle(ref, () => ({
    requestRevision: (f, r) => void requestRevision(f, r),
    focusComposer: () => textarea.current?.focus(),
  }))

  const decide = (id: number, decision: 'approved' | 'rejected') =>
    setMessages((ms) => ms.map((m) => (m.id === id && m.role === 'draft' ? { ...m, decision } : m)))

  const comparable = att.chips.some((c) => c.selected && ready(c) && (c.purpose === 'comparison' || c.purpose === 'revision'))
  const disabled = !auditId

  return (
    <aside
      className={`copilot${dragging ? ' dragging' : ''}`}
      aria-label="SPEC Copilot"
      data-open={open ? 'yes' : 'no'}
      inert={!open}
      onDragOver={(e) => {
        if (disabled) return
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={(e) => {
        if (e.currentTarget === e.target) setDragging(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        if (!disabled && e.dataTransfer.files.length) att.add(e.dataTransfer.files, purpose)
      }}
    >
      <header className="copilot-head">
        <span className="mini"><SpecMascot state="idle" title="SPEC" /></span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <b>SPEC Copilot</b>
          <small>Контекстный AI-помощник</small>
        </div>
        <button type="button" className="icon-btn" onClick={() => setMessages([])} aria-label="Новый чат" title="Новый чат">
          <Icon name="plus" size={18} />
        </button>
        <button ref={closeBtn} type="button" className="icon-btn close" onClick={onClose} aria-label="Закрыть Copilot">
          <Icon name="x" size={18} />
        </button>
      </header>

      <div className="conversation">
        <div className="context-bar" data-testid="copilot-context">
          <Icon name="doc" size={14} />
          <span className="grow">
            {result ? (
              <>
                Контекст · {result.documents.map((d) => d.filename).join(', ')} · Аудит <span className="mono">#{result.audit_id.slice(0, 6)}</span>
                {context.requirement && <> · Требование <b className="mono">{requirementLabel(context.requirement)}</b></>}
                {context.finding && <> · Замечание «{context.finding.title}»</>}
              </>
            ) : (
              'Аудит ещё не запущен'
            )}
          </span>
          {(context.requirement || context.finding) && (
            <button type="button" className="icon-btn" onClick={clearContext} aria-label="Сбросить выбранный контекст">
              <Icon name="x" size={14} />
            </button>
          )}
        </div>

        <div className="reply intro">
          {disabled
            ? 'Привет! Я SPEC. Загрузите техническое задание и запустите аудит — после этого я отвечу на вопросы с цитатами из источника.'
            : `Привет! Я SPEC. ${result ? `Вердикт: ${VERDICT_LABELS[result.readiness.verdict]}. ` : ''}Задайте вопрос о требованиях или прикрепите документы для контекста и сравнения.`}
        </div>

        <div className="history" ref={history} aria-live="polite">
          {messages.map((m) => (
            <MessageView key={m.id} m={m} filenames={filenames} openSource={openSource} onDecide={decide} onRevalidate={onRevalidate} chips={att.chips} />
          ))}
          {busy && <div className="reply pending" role="status">SPEC готовит ответ…</div>}
        </div>

        {!disabled && messages.length === 0 && (
          <div className="suggestions">
            {[...SUGGESTIONS, ...(context.finding ? [`Предложить исправление: ${context.finding.title}`] : [])].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => {
                  setText(s)
                  textarea.current?.focus()
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault()
          if (!text.trim() && !selectedIds.length) return
          void ask(text)
        }}
      >
        {att.chips.length > 0 && (
          <ul className="attachments" aria-label="Вложения">
            {att.chips.map((c) => (
              <li key={c.localId} className={`chip ${c.state}`} data-state={c.state}>
                <input
                  type="checkbox"
                  checked={c.selected}
                  disabled={c.state !== 'extracted'}
                  onChange={() => att.toggle(c.localId)}
                  aria-label={`Использовать ${c.file.name} в запросе`}
                />
                <span className="ftype">{fileTypeLabel(c.file.name)}</span>
                <span className="grow">
                  <span className="name">{c.file.name}</span>
                  <span className="meta">
                    {formatBytes(c.file.size)} · {PURPOSE_LABELS[c.purpose]} ·{' '}
                    {c.state === 'uploading' && 'загрузка…'}
                    {c.state === 'extracted' && <span className="ok">текст извлечён</span>}
                    {c.state === 'removing' && 'удаление…'}
                    {c.state === 'error' && <span className="bad">{c.error}</span>}
                  </span>
                </span>
                {c.state === 'error' && (
                  <button type="button" className="icon-btn" onClick={() => att.retry(c.localId)} aria-label={`Повторить ${c.file.name}`}>
                    <Icon name="retry" size={14} />
                  </button>
                )}
                <button type="button" className="icon-btn" onClick={() => void att.remove(c.localId)} aria-label={`Удалить ${c.file.name}`} disabled={c.state === 'uploading' || c.state === 'removing'}>
                  <Icon name="x" size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <textarea
          ref={textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              e.currentTarget.form?.requestSubmit()
            }
          }}
          aria-label="Ваш вопрос"
          placeholder={disabled ? 'Сначала запустите аудит' : 'Спросите SPEC о требованиях…'}
          rows={2}
          maxLength={4000}
          disabled={disabled}
        />
        <div className="toolbar">
          <button type="button" className="attach" onClick={() => picker.current?.click()} aria-label="Прикрепить файлы" disabled={disabled}>
            <Icon name="clip" size={17} />
          </button>
          <input
            ref={picker}
            type="file"
            multiple
            hidden
            accept={ACCEPT_ATTRIBUTE}
            onChange={(e) => {
              if (e.target.files?.length) att.add(e.target.files, purpose)
              e.target.value = ''
            }}
          />
          <select value={purpose} onChange={(e) => setPurpose(e.target.value as AttachmentPurpose)} aria-label="Назначение вложений" disabled={disabled}>
            <option value="context">Контекст</option>
            <option value="comparison">Сравнение</option>
            <option value="revision">Новая редакция</option>
          </select>
          {comparable && (
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => void compare()} disabled={busy}>
              <Icon name="swap" size={14} /> Сравнить
            </button>
          )}
          <button type="submit" className="send" aria-label="Отправить" disabled={disabled || busy || (!text.trim() && !selectedIds.length)}>
            <Icon name="send" size={17} />
          </button>
        </div>
        <small className="hint">PDF, MD, TXT · до 5 МБ · можно перетащить</small>
      </form>

      <footer className="copilot-foot">
        <label>
          <input type="radio" name="copilot-mode" checked={mode === 'offline'} onChange={() => setMode('offline')} /> Офлайн
        </label>
        <label>
          <input type="radio" name="copilot-mode" checked={mode === 'live'} onChange={() => setMode('live')} /> DeepSeek
        </label>
        {live && (
          <label className="consent-inline">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} /> согласие на отправку текста
          </label>
        )}
        <span className="mode-note">
          {live ? 'Ответы модели DeepSeek с проверкой цитат' : 'Офлайн: поиск фрагментов по источникам, без модели'}
        </span>
      </footer>
    </aside>
  )
})

function MessageView({
  m,
  filenames,
  openSource,
  onDecide,
  onRevalidate,
  chips,
}: {
  m: Message
  filenames: Record<string, string>
  openSource: Props['openSource']
  onDecide: (id: number, d: 'approved' | 'rejected') => void
  onRevalidate: (file: File) => void
  chips: AttachmentChip[]
}) {
  if (m.role === 'user')
    return (
      <div className="question">
        {m.context && <span className="qctx">{m.context}</span>}
        {m.files.length > 0 && <span className="qfiles"><Icon name="clip" size={12} /> {m.files.join(', ')}</span>}
        {m.text}
      </div>
    )
  if (m.role === 'error')
    return (
      <div className="reply error" role="alert">
        <Icon name="alert" size={15} /> {m.text}
      </div>
    )
  if (m.role === 'answer') {
    const r = m.response
    return (
      <div className="reply">
        <span className="who">SPEC · {m.mode === 'live' ? 'DeepSeek' : 'офлайн-поиск'}</span>
        <p style={{ whiteSpace: 'pre-wrap' }}>{r.answer}</p>
        {r.evidence.length > 0 && (
          <div className="cites">
            <span className="label">Источники</span>
            <EvidenceList items={r.evidence} filenames={filenames} onOpen={openSource} />
          </div>
        )}
        {r.clarification_questions.length > 0 && (
          <div className="cites">
            <span className="label">Вопросы заинтересованным сторонам</span>
            <ul>{r.clarification_questions.map((q) => <li key={q}>{q}</li>)}</ul>
          </div>
        )}
        {r.uncertainty && <p className="uncertainty">{r.uncertainty}</p>}
      </div>
    )
  }
  if (m.role === 'comparison') {
    const r = m.result
    const revision = chips.find((c) => c.purpose === 'revision' && c.state === 'extracted')
    return (
      <div className="reply">
        <span className="who">SPEC · сравнение документов</span>
        <p>{r.relationship}</p>
        {r.changes.map((c, i) => (
          <div key={i} className="change">
            <b>{c.kind}</b> · <span className="muted">{c.alignment}</span>
            <p>{c.description}</p>
            {c.uncertainty && <p className="uncertainty">{c.uncertainty}</p>}
            <EvidenceList items={c.evidence} filenames={filenames} onOpen={openSource} />
          </div>
        ))}
        {r.questions.length > 0 && (
          <div className="cites">
            <span className="label">Вопросы</span>
            <ul>{r.questions.map((q) => <li key={q}>{q}</li>)}</ul>
          </div>
        )}
        {revision && (
          <button type="button" className="btn btn-secondary btn-sm" style={{ marginTop: 8 }} onClick={() => onRevalidate(revision.file)}>
            <Icon name="retry" size={14} /> Перепроверить новую редакцию отдельным аудитом
          </button>
        )}
      </div>
    )
  }
  const d = m.draft
  return (
    <div className="reply draft" data-decision={m.decision}>
      <span className="who">Черновик исправления · {m.requirement}</span>
      <p className="small muted">Замечание: {m.findingTitle}</p>
      <div className="draft-block">
        <span className="label">Было</span>
        <p>{d.original_text}</p>
      </div>
      <div className="draft-block proposed">
        <span className="label">Предлагается</span>
        <p>{d.proposed_revision ?? 'Модель не предложила однозначную формулировку — нужны решения заинтересованных сторон.'}</p>
      </div>
      {d.alternatives.length > 0 && (
        <div className="cites"><span className="label">Альтернативы</span><ul>{d.alternatives.map((a) => <li key={a}>{a}</li>)}</ul></div>
      )}
      <p className="small">{d.explanation}</p>
      {d.assumptions.length > 0 && (
        <div className="cites"><span className="label">Допущения</span><ul>{d.assumptions.map((a) => <li key={a}>{a}</li>)}</ul></div>
      )}
      {d.decisions.length > 0 && (
        <div className="cites"><span className="label">Решения заинтересованных сторон</span><ul>{d.decisions.map((a) => <li key={a}>{a}</li>)}</ul></div>
      )}
      {d.acceptance_tests.length > 0 && (
        <div className="cites"><span className="label">Приёмочные тесты</span><ul>{d.acceptance_tests.map((a) => <li key={a}>{a}</li>)}</ul></div>
      )}
      {d.evidence.length > 0 && <EvidenceList items={d.evidence} filenames={filenames} onOpen={openSource} />}
      <div className="draft-actions">
        {m.decision === 'pending' ? (
          <>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => onDecide(m.id, 'approved')}>Одобрить черновик</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => onDecide(m.id, 'rejected')}>Отклонить</button>
          </>
        ) : (
          <span className="small">
            {m.decision === 'approved' ? 'Одобрено вами.' : 'Отклонено.'} Исходный аудит не изменён — внесите правку в ТЗ и перепроверьте документ.
          </span>
        )}
        {d.proposed_revision && (
          <button type="button" className="icon-btn" onClick={() => void navigator.clipboard?.writeText(d.proposed_revision!)} aria-label="Скопировать предложенную формулировку">
            <Icon name="copy" size={15} />
          </button>
        )}
      </div>
    </div>
  )
}
