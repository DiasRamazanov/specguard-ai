import type { AuditStatus, EventStage } from '../api/types'
import { Icon } from '../components/Icons'
import { ModeBadge } from '../components/ModeBadge'
import { PIPELINE, STAGE_LABELS } from '../labels'
import type { AuditController } from '../state/useAudit'

type StepState = 'done' | 'active' | 'pending' | 'skipped'

/** Step states derived only from events the backend actually reported. */
export function pipelineStates(status: AuditStatus | null): Record<EventStage, StepState> {
  const out = {} as Record<EventStage, StepState>
  const events = status?.events ?? []
  const seen = new Set(events.map((e) => e.stage))
  const finished = status?.status === 'completed' || status?.status === 'failed'
  const last = [...events].reverse().find((e) => PIPELINE.some((p) => p.stage === e.stage))?.stage
  const lastIndex = PIPELINE.findIndex((p) => p.stage === last)
  PIPELINE.forEach(({ stage }, i) => {
    if (seen.has(stage)) out[stage] = !finished && stage === last ? 'active' : 'done'
    else if (finished || i < lastIndex) out[stage] = 'skipped'
    else out[stage] = 'pending'
  })
  return out
}

export function ProgressView({ audit }: { audit: AuditController }) {
  const states = pipelineStates(audit.status)
  const failed = audit.phase === 'failed'
  return (
    <div className="content" style={{ maxWidth: 860 }}>
      <div className="card">
        <div className="card-title">
          <h2 style={{ flex: 1 }}>Анализ требований</h2>
          <ModeBadge mode={audit.mode} />
        </div>
        <p className="muted small" style={{ marginBottom: 14 }}>
          Этапы отображаются по событиям сервера. {audit.mode === 'offline' && 'Семантические этапы в офлайн-режиме не выполняются.'}
        </p>
        <div className="pipeline" aria-live="polite">
          {PIPELINE.map(({ stage, label }) => (
            <div key={stage} className={`pipe-step ${states[stage]}`} data-stage={stage}>
              <span className="st">{states[stage] === 'done' && <Icon name="check" size={13} />}</span>
              <span style={{ flex: 1 }}>{label}</span>
              {states[stage] === 'skipped' && <span className="small">не выполнялось</span>}
            </div>
          ))}
        </div>
        {failed && (
          <div className="notice notice-error" role="alert" style={{ marginTop: 14 }}>
            <Icon name="alert" size={18} />
            <span style={{ flex: 1 }}>{audit.error ?? 'Аудит завершился ошибкой.'}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={audit.newAudit}>
              Новый анализ
            </button>
          </div>
        )}
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Журнал событий</h3>
        <ol className="event-log">
          {(audit.status?.events ?? []).map((e) => (
            <li key={e.sequence}>
              <span className="mono">{new Date(e.time).toLocaleTimeString('ru-RU')}</span>
              <span>{STAGE_LABELS[e.stage]}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
