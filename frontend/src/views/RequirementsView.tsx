import { EvidenceList } from '../components/Evidence'
import { Icon } from '../components/Icons'
import { ASSESSMENT_LABELS, CRITERION_STATUS_LABELS, SEVERITY_LABELS, criterionLabel } from '../labels'
import { findingsById, requirementLabel, type WorkspaceProps } from './shared'

export function RequirementsView(props: WorkspaceProps & { selectedId?: string }) {
  const { result, filenames, openSource, askSpec, navigate, selectedId } = props
  const assessments = Object.fromEntries(result.assessments.map((a) => [a.requirement_id, a]))
  const findings = findingsById(result)
  const selected = result.requirements.find((r) => r.requirement_id === selectedId)

  return (
    <div className="content">
      <h1>Требования <span className="muted" style={{ fontWeight: 600 }}>({result.requirements.length})</span></h1>
      <div className="split">
        <div className="card" style={{ padding: 8 }}>
          {result.requirements.length === 0 && <p className="empty">Требования не извлечены.</p>}
          <div className="list" role="list" aria-label="Список требований">
            {result.requirements.map((r) => {
              const a = assessments[r.requirement_id]
              const n = a?.finding_ids?.length ?? 0
              return (
                <button
                  key={r.requirement_id}
                  type="button"
                  className="list-row"
                  aria-current={r.requirement_id === selectedId}
                  onClick={() => navigate('requirements', r.requirement_id)}
                >
                  <span className="mono" style={{ color: 'var(--primary)', flex: 'none', minWidth: 64 }}>{requirementLabel(r)}</span>
                  <span className="grow">
                    <span className="title" style={{ fontWeight: 500, whiteSpace: 'nowrap' }}>{r.summary}</span>
                    <span className="sub">{r.section ?? r.kind}</span>
                  </span>
                  {n > 0 && <span className="badge badge-major">{n}</span>}
                </button>
              )
            })}
          </div>
        </div>

        <div className="card">
          {!selected ? (
            <p className="empty">Выберите требование, чтобы увидеть доказательства и оценку.</p>
          ) : (
            <>
              <div className="detail-head">
                <h2><span className="mono" style={{ color: 'var(--primary)' }}>{requirementLabel(selected)}</span></h2>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => askSpec({ requirement: selected })}>
                  <Icon name="chat" size={15} /> Спросить SPEC
                </button>
              </div>
              <div className="detail-meta">
                <span>{selected.kind}</span>
                {selected.section && <span>§ {selected.section}</span>}
                {assessments[selected.requirement_id] && (
                  <span className="badge badge-neutral">{ASSESSMENT_LABELS[assessments[selected.requirement_id].status]}</span>
                )}
                <span className="mono">{selected.requirement_id}</span>
              </div>
              <p>{selected.summary}</p>
              {selected.uncertainty && <p className="small muted" style={{ marginTop: 6 }}>{selected.uncertainty}</p>}

              <div className="section">
                <h4>Первоисточник</h4>
                <EvidenceList items={selected.evidence} filenames={filenames} onOpen={openSource} />
              </div>

              {!!assessments[selected.requirement_id]?.criteria?.length && (
                <div className="section">
                  <h4>Оценка по критериям</h4>
                  <table className="table">
                    <tbody>
                      {assessments[selected.requirement_id].criteria!.map((c) => (
                        <tr key={c.criterion}>
                          <td style={{ width: 150, fontWeight: 600 }}>{criterionLabel(c.criterion)}</td>
                          <td style={{ width: 150 }}>{CRITERION_STATUS_LABELS[c.status] ?? c.status}</td>
                          <td className="muted">{c.explanation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="section">
                <h4>Связанные замечания</h4>
                {(assessments[selected.requirement_id]?.finding_ids ?? []).length === 0 ? (
                  <p className="muted small">Нет замечаний.</p>
                ) : (
                  <div className="list">
                    {assessments[selected.requirement_id].finding_ids!.map((id) => findings[id]).filter(Boolean).map((f) => (
                      <button key={f.finding_id} type="button" className="list-row" onClick={() => navigate('findings', f.finding_id)}>
                        <span className="grow"><span className="title">{f.title}</span></span>
                        <span className={`badge badge-${f.severity}`}>{SEVERITY_LABELS[f.severity]}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {!!selected.relationships?.length && (
                <div className="section">
                  <h4>Связи</h4>
                  <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
                    {selected.relationships.map((r) => <li key={r}>{r}</li>)}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
