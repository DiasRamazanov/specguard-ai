import { useEffect, useState } from 'react'
import { ApiError, type SpecGuardClient } from '../api/client'
import { Icon } from '../components/Icons'
import { Markdown } from '../components/Markdown'
import { ModeBadge } from '../components/ModeBadge'
import { SEVERITY_LABELS, SEVERITY_ORDER } from '../labels'
import { Verdict } from './OverviewView'
import type { WorkspaceProps } from './shared'

export function ReportView(props: WorkspaceProps & { client: SpecGuardClient }) {
  const { result, client } = props
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    client
      .report(result.audit_id)
      .then((md) => alive && setMarkdown(md))
      .catch((e) => alive && setError(e instanceof ApiError ? e.detail : 'Не удалось получить отчёт.'))
    return () => {
      alive = false
    }
  }, [client, result.audit_id])

  const download = () => {
    if (!markdown) return
    const url = URL.createObjectURL(new Blob([markdown], { type: 'text/markdown;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `specguard-report-${result.audit_id.slice(0, 8)}.md`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const counts = result.readiness.confirmed_by_severity ?? {}

  return (
    <div className="content">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h1 style={{ flex: 1 }}>Итоговый отчёт</h1>
        <ModeBadge mode={result.mode} model={result.mode === 'live' ? result.model : undefined} />
        <button type="button" className="btn btn-secondary" onClick={download} disabled={!markdown}>
          <Icon name="download" size={16} /> Скачать Markdown
        </button>
      </div>
      <Verdict result={result} />

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Подтверждённые замечания</h3>
          <table className="table">
            <tbody>
              {SEVERITY_ORDER.map((s) => (
                <tr key={s}>
                  <td><span className={`badge badge-${s}`}>{SEVERITY_LABELS[s]}</span></td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>{counts[s] ?? 0}</td>
                </tr>
              ))}
              <tr>
                <td>Требуют уточнения</td>
                <td style={{ textAlign: 'right', fontWeight: 700 }}>{result.readiness.clarification_count}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 10 }}>Сведения о запуске</h3>
          <table className="table">
            <tbody>
              <tr><td>Аудит</td><td className="mono">{result.audit_id}</td></tr>
              <tr><td>Создан</td><td>{new Date(result.created_at).toLocaleString('ru-RU')}</td></tr>
              <tr><td>Версия агента</td><td className="mono">{result.agent_version}</td></tr>
              <tr><td>Модель</td><td>{result.model}</td></tr>
              <tr><td>Документы</td><td>{result.documents.map((d) => d.filename).join(', ')}</td></tr>
              <tr><td>Отклонённые кандидаты</td><td>{result.rejected_candidates.length}</td></tr>
            </tbody>
          </table>
          {!!result.usage?.length && (
            <>
              <h4 className="small muted" style={{ margin: '12px 0 4px' }}>Расход модели</h4>
              <pre className="small mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{JSON.stringify(result.usage, null, 1)}</pre>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 6 }}>Отчёт</h3>
        {error && <div className="notice notice-error">{error}</div>}
        {!markdown && !error && (
          <div className="skeleton" role="status" aria-label="Загрузка отчёта" style={{ marginTop: 10 }}>
            <i /><i /><i /><i /><i /><i /><i /><i />
          </div>
        )}
        {markdown && <Markdown source={markdown} />}
      </div>
    </div>
  )
}
