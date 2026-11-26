import { useState } from 'react'
import type { Severity } from '../api/types'
import { EvidenceList } from '../components/Evidence'
import { Icon } from '../components/Icons'
import { SpecMascot } from '../mascot/SpecMascot'
import { FINDING_STATUS_LABELS, SEVERITY_LABELS, SEVERITY_ORDER, criterionLabel, isContradiction } from '../labels'
import { bySeverity, requirementLabel, requirementsById, type WorkspaceProps } from './shared'

type Tab = 'analysis' | 'impact' | 'recommendation' | 'source'

export function FindingsView(props: WorkspaceProps & { selectedId?: string; contradictionsOnly?: boolean }) {
  const { result, filenames, openSource, askSpec, requestRevision, navigate, selectedId, contradictionsOnly } = props
  const [filter, setFilter] = useState<Severity | 'all'>('all')
  const [tab, setTab] = useState<Tab>('analysis')
  const reqs = requirementsById(result)
  const view = contradictionsOnly ? 'contradictions' : 'findings'
  const pool = result.findings.filter((f) => (contradictionsOnly ? isContradiction(f) : true)).sort(bySeverity)
  const list = pool.filter((f) => filter === 'all' || f.severity === filter)
  const selected = pool.find((f) => f.finding_id === selectedId)
  const pairReqs = selected ? (selected.requirement_ids ?? []).map((id) => reqs[id]).filter(Boolean) : []

  return (
    <div className="content">
      <h1>
        {contradictionsOnly ? 'Противоречия' : 'Замечания'} <span className="muted" style={{ fontWeight: 600 }}>({pool.length})</span>
      </h1>
      <div className="split">
        <div className="card" style={{ padding: 10 }}>
          <div className="filters" role="group" aria-label="Фильтр по важности">
            <button type="button" className="chip-filter" aria-pressed={filter === 'all'} onClick={() => setFilter('all')}>Все</button>
            {SEVERITY_ORDER.filter((s) => pool.some((f) => f.severity === s)).map((s) => (
              <button key={s} type="button" className="chip-filter" aria-pressed={filter === s} onClick={() => setFilter(s)}>
                {SEVERITY_LABELS[s]}
              </button>
            ))}
          </div>
          {list.length === 0 && (
            <div className="empty">
              {contradictionsOnly
                ? result.mode === 'offline'
                  ? 'Противоречия выявляет семантическая проверка DeepSeek; в офлайн-режиме она не выполнялась.'
                  : 'Противоречий не обнаружено.'
                : 'Замечаний нет.'}
            </div>
          )}
          <div className="list">
            {list.map((f) => (
              <button
                key={f.finding_id}
                type="button"
                className="list-row"
                aria-current={f.finding_id === selectedId}
                onClick={() => {
                  setTab('analysis')
                  navigate(view, f.finding_id)
                }}
              >
                <Icon name={isContradiction(f) ? 'swap' : 'alert'} size={18} style={{ flex: 'none', color: f.severity === 'critical' ? 'var(--critical)' : 'var(--warning)' }} />
                <span className="grow">
                  <span className="title">{f.title}</span>
                  <span className="sub">
                    {(f.requirement_ids ?? []).map((id) => (reqs[id] ? requirementLabel(reqs[id]) : id)).join(' ↔ ') || criterionLabel(f.criterion)}
                  </span>
                </span>
                <span className={`badge badge-${f.severity}`}>{SEVERITY_LABELS[f.severity]}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="card" data-testid="finding-detail">
          {!selected ? (
            <p className="empty">Выберите замечание, чтобы увидеть доказательства и рекомендации.</p>
          ) : (
            <>
              <div className="detail-head">
                <h2>{selected.title}</h2>
                <span className={`badge badge-${selected.severity}`}>{SEVERITY_LABELS[selected.severity]}</span>
              </div>
              <div className="detail-meta">
                <span>{criterionLabel(selected.criterion)}</span>
                <span>{selected.scope === 'global' ? 'Общая проверка' : 'Отдельное требование'}</span>
                <span className="badge badge-neutral">{FINDING_STATUS_LABELS[selected.status]}</span>
                <span className="mono">{selected.finding_id}</span>
              </div>

              {pairReqs.length >= 2 && (
                <div className="compare-pair" style={{ marginBottom: 14 }}>
                  <button type="button" className="evidence" onClick={() => navigate('requirements', pairReqs[0].requirement_id)}>
                    <span className="badge badge-neutral mono">{requirementLabel(pairReqs[0])}</span>
                    <p style={{ marginTop: 6 }}>{pairReqs[0].summary}</p>
                  </button>
                  <span className="swap" aria-hidden="true"><Icon name="swap" /></span>
                  <button type="button" className="evidence" onClick={() => navigate('requirements', pairReqs[1].requirement_id)}>
                    <span className="badge badge-neutral mono">{requirementLabel(pairReqs[1])}</span>
                    <p style={{ marginTop: 6 }}>{pairReqs[1].summary}</p>
                  </button>
                </div>
              )}

              <div className="tabs" role="tablist">
                {(
                  [
                    ['analysis', 'Анализ'],
                    ['impact', 'Влияние'],
                    ['recommendation', 'Рекомендация'],
                    ['source', 'Источник'],
                  ] as [Tab, string][]
                ).map(([id, label]) => (
                  <button key={id} type="button" role="tab" className="tab" aria-selected={tab === id} onClick={() => setTab(id)}>
                    {label}
                  </button>
                ))}
              </div>

              <div role="tabpanel">
                {tab === 'analysis' && (
                  <div className="insight">
                    <SpecMascot state="idle" title="SPEC" />
                    <div>
                      <p>{selected.explanation}</p>
                      {selected.conflict_scenario && <p style={{ marginTop: 8 }}><b>Сценарий конфликта:</b> {selected.conflict_scenario}</p>}
                      {selected.uncertainty && <p className="small" style={{ marginTop: 8, opacity: 0.8 }}>Неопределённость: {selected.uncertainty}</p>}
                    </div>
                  </div>
                )}
                {tab === 'impact' && <p>{selected.impact}</p>}
                {tab === 'recommendation' && (
                  <>
                    <p>{selected.recommendation}</p>
                    {selected.review_explanation && <p className="small muted" style={{ marginTop: 8 }}>Проверка критиком: {selected.review_explanation}</p>}
                  </>
                )}
                {tab === 'source' && (
                  <>
                    <EvidenceList items={selected.evidence} filenames={filenames} onOpen={openSource} />
                    {!!selected.counterevidence?.length && (
                      <div className="section">
                        <h4>Контрдоказательства</h4>
                        <EvidenceList items={selected.counterevidence} filenames={filenames} onOpen={openSource} />
                      </div>
                    )}
                  </>
                )}
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => askSpec({ finding: selected })}>
                  <Icon name="chat" size={15} /> Спросить SPEC
                </button>
                {(selected.requirement_ids ?? []).map((rid) => (
                  <button key={rid} type="button" className="btn btn-ghost btn-sm" onClick={() => requestRevision(selected, rid)}>
                    <Icon name="pen" size={15} /> Черновик исправления {reqs[rid] ? requirementLabel(reqs[rid]) : ''}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
