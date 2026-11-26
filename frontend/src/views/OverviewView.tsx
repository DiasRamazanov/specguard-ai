import { Icon } from '../components/Icons'
import { OfflineNotice } from '../components/ModeBadge'
import { SEVERITY_LABELS, VERDICT_LABELS, criterionLabel, isContradiction } from '../labels'
import { SEVERITY_COLOR, bySeverity, findingsById, type WorkspaceProps } from './shared'

export function Verdict({ result }: Pick<WorkspaceProps, 'result'>) {
  const { verdict, rationale } = result.readiness
  return (
    <div className={`verdict ${verdict}`} data-testid="verdict">
      <span className="verdict-icon">
        <Icon name={verdict === 'ready' ? 'check' : verdict === 'unable_to_determine' ? 'info' : 'alert'} size={20} />
      </span>
      <div style={{ flex: 1 }}>
        <h3>{VERDICT_LABELS[verdict]}</h3>
        <p className="muted small">{rationale}</p>
      </div>
    </div>
  )
}

/** Per-criterion share of "valid" assessments; only criteria the backend actually assessed. */
export function criterionScores(result: WorkspaceProps['result']) {
  const tally = new Map<string, { valid: number; total: number }>()
  for (const a of result.assessments) {
    for (const c of a.criteria ?? []) {
      if (c.status === 'not_applicable') continue
      const t = tally.get(c.criterion) ?? { valid: 0, total: 0 }
      t.total++
      if (c.status === 'valid') t.valid++
      tally.set(c.criterion, t)
    }
  }
  return [...tally.entries()].map(([criterion, t]) => ({ criterion, pct: Math.round((t.valid / t.total) * 100), total: t.total }))
}

function pct(n: number, d: number) {
  return d > 0 ? Math.round((n / d) * 100) : 0
}

export function OverviewView(props: WorkspaceProps) {
  const { result, navigate } = props
  const crit = result.readiness.confirmed_by_severity?.critical ?? 0
  const contradictions = result.findings.filter(isContradiction).length
  const scores = criterionScores(result)
  const cov = result.coverage
  const byId = findingsById(result)
  const priority = (result.readiness.priority_finding_ids.map((id) => byId[id]).filter(Boolean).length
    ? result.readiness.priority_finding_ids.map((id) => byId[id]).filter(Boolean)
    : [...result.findings].sort(bySeverity)
  ).slice(0, 5)

  return (
    <div className="content">
      <div className="page-head">
        <h1>Результаты аудита</h1>
        {cov.complete ? (
          <span className="badge badge-success"><Icon name="check" size={13} /> Анализ завершён</span>
        ) : (
          <span className="badge badge-major"><Icon name="info" size={13} /> Покрытие неполное</span>
        )}
      </div>
      {result.mode === 'offline' && <OfflineNotice />}
      <Verdict result={result} />

      <div className="stats">
        <div className="card stat">
          <span className="stat-icon"><Icon name="doc" size={30} /></span>
          <div><b>{result.requirements.length}</b><span>Требований</span></div>
        </div>
        <div className="card stat">
          <span className="stat-icon warn"><Icon name="alert" size={30} /></span>
          <div><b>{result.findings.length}</b><span>Замечаний</span></div>
        </div>
        <div className="card stat">
          <span className="stat-icon crit"><Icon name="shield" size={30} /></span>
          <div><b>{crit}</b><span>Критических</span></div>
        </div>
        <div className="card stat">
          <span className="stat-icon"><Icon name="swap" size={30} /></span>
          <div><b>{contradictions}</b><span>Противоречий</span></div>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          {scores.length ? (
            <>
              <div className="card-title"><h3>Оценка по критериям ISO/IEC/IEEE 29148</h3></div>
              {scores.map((s) => (
                <div className="bar-row" key={s.criterion}>
                  <span>{criterionLabel(s.criterion)}</span>
                  <span className="bar" role="meter" aria-valuenow={s.pct} aria-valuemin={0} aria-valuemax={100} aria-label={criterionLabel(s.criterion)}><i style={{ width: `${s.pct}%` }} /></span>
                  <span className="val">{s.pct}%</span>
                </div>
              ))}
            </>
          ) : (
            <>
              <div className="card-title"><h3>Покрытие проверки</h3></div>
              <p className="muted small" style={{ marginBottom: 8 }}>
                Оценки по критериям появляются после семантической проверки. Ниже — фактическое покрытие этого запуска.
              </p>
            </>
          )}
          <div style={{ marginTop: scores.length ? 12 : 0 }}>
            <div className="bar-row">
              <span>Блоков просмотрено</span>
              <span className="bar"><i style={{ width: `${pct(cov.extraction_blocks_reviewed, cov.source_blocks)}%` }} /></span>
              <span className="val">{cov.extraction_blocks_reviewed}/{cov.source_blocks}</span>
            </div>
            <div className="bar-row">
              <span>Требований оценено</span>
              <span className="bar"><i style={{ width: `${pct(cov.individually_assessed, cov.requirements)}%` }} /></span>
              <span className="val">{cov.individually_assessed}/{cov.requirements}</span>
            </div>
            <div className="bar-row">
              <span>Общая проверка</span>
              <span className="small">{cov.global_pass_complete ? 'выполнена' : 'не выполнена'}</span>
              <span />
            </div>
            <div className="bar-row">
              <span>Независимый критик</span>
              <span className="small">{cov.critic_complete ? 'выполнен' : 'не выполнен'}</span>
              <span />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <h3>Приоритетные замечания</h3>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => navigate('findings')}>Все</button>
          </div>
          {priority.length === 0 ? (
            <p className="muted">Замечаний не найдено.</p>
          ) : (
            <div className="list">
              {priority.map((f) => (
                <button key={f.finding_id} type="button" className="list-row" onClick={() => navigate(isContradiction(f) ? 'contradictions' : 'findings', f.finding_id)}>
                  <Icon name="alert" size={18} style={{ color: SEVERITY_COLOR[f.severity], flex: 'none' }} />
                  <span className="grow"><span className="title">{f.title}</span></span>
                  <span className={`badge badge-${f.severity}`}>{SEVERITY_LABELS[f.severity]}</span>
                  <Icon name="chevron" size={16} className="chev" />
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {!!result.limitations?.length && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Ограничения анализа</h3>
          <ul style={{ margin: 0, paddingLeft: 18 }} className="small">
            {result.limitations.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}
