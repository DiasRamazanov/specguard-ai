import { publicDemo, publicModeNotice } from '../publicDemo'
import { demoSpecification } from './demoSpecification'
import { useRef, useState } from 'react'
import { ACCEPT_ATTRIBUTE } from '../api/client'
import { Icon } from '../components/Icons'
import { SpecMascot } from '../mascot/SpecMascot'
import { fileTypeLabel, formatBytes } from '../labels'
import type { AuditController } from '../state/useAudit'

/** Thin flowing lines behind the hero, as in references/frontend/02–03. */
function HeroWaves() {
  const lines = Array.from({ length: 14 }, (_, i) => {
    const y = 60 + i * 18
    const a = 40 + i * 4
    return `M0 ${y} C 160 ${y - a}, 320 ${y + a}, 480 ${y} S 800 ${y - a / 2}, 900 ${y + 10}`
  })
  return (
    <svg className="hero-waves" viewBox="0 0 900 420" preserveAspectRatio="none" aria-hidden="true">
      {lines.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="#8b5cf6" strokeOpacity={0.05 + (i % 4) * 0.025} strokeWidth="1" />
      ))}
    </svg>
  )
}

export function SetupView({ audit }: { audit: AuditController }) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)
  const ready = audit.documents.filter((d) => d.state === 'ready')
  const uploading = audit.documents.some((d) => d.state === 'uploading')
  const liveBlocked = audit.mode === 'live' && !audit.consent
  const canStart = ready.length > 0 && !uploading && !liveBlocked

  return (
    <div className="content">
      <section className="hero">
        <HeroWaves />
        <div>
          <span className="badge badge-neutral" style={{ padding: '5px 12px' }}>
            <Icon name="sparkle" size={14} /> AI-агент для анализа ТЗ
          </span>
          <h1 style={{ marginTop: 18 }}>
            Проверьте ТЗ на качество
            <span className="ai">с AI-агентом</span>
          </h1>
          <p className="lead">
            Автоматический аудит требований по ISO/IEC/IEEE 29148 для FinTech-проектов: находим противоречия, пропуски и риски до начала
            разработки. Каждое замечание подкреплено цитатой из документа.
          </p>
          <button type="button" className="btn btn-secondary" style={{ marginTop: 16 }} disabled={audit.starting}
            aria-describedby="demo-description" onClick={() => void audit.start(demoSpecification())}>
            Запустить демо-анализ
          </button>
          <p id="demo-description" className="small muted">Офлайн-проверка синтетического ТЗ о выдаче наличных.</p>
          <div className="features">
            <span className="feature"><Icon name="bolt" size={24} /> Автоматический<br />анализ</span>
            <span className="feature"><Icon name="layers" size={24} /> Аргументированные<br />находки</span>
            <span className="feature"><Icon name="shield" size={24} /> Оценка<br />готовности</span>
            <span className="feature"><Icon name="report" size={24} /> Отчёт<br />и рекомендации</span>
          </div>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="greet">
            <div>
              <b>Привет! Я SPEC 👋</b>
              Загрузите техническое задание, и я проверю его на качество, противоречия и риски.
            </div>
          </div>
          <span className="dot" style={{ left: '8%', top: '12%' }} />
          <span className="dot" style={{ right: '6%', top: '46%' }} />
          <span className="dot" style={{ left: '22%', bottom: '10%', width: 6, height: 6 }} />
          <svg className="burst" width="44" height="52" viewBox="0 0 44 52">
            <path d="M30 6 40 18M8 24h22M14 44l18-10" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
          </svg>
          <SpecMascot state="greeting" decorative />
          <span className="floor" />
        </div>
      </section>

      <section className="card" aria-labelledby="upload-title">
        <div className="stepper" aria-hidden="true">
          <span className="dot on">1</span> Загрузка <span className="line" />
          <span className="dot">2</span> Настройка <span className="line" />
          <span className="dot">3</span> Анализ
        </div>
        <h2 id="upload-title">Загрузите техническое задание</h2>
        <p className="muted small" style={{ margin: '4px 0 16px' }}>
          Поддерживаются PDF, Markdown и TXT (до 5 МБ, можно несколько файлов). Разбор PDF выполняется на сервере в Linux или macOS.
        </p>

        <div className="upload-card">
          <div
            className={`dropzone${over ? ' over' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setOver(true)
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setOver(false)
              if (e.dataTransfer.files.length) audit.addFiles(e.dataTransfer.files)
            }}
            data-testid="dropzone"
          >
            <div className="cloud"><Icon name="cloud" size={34} /></div>
            Перетащите файлы сюда
            <br />
            или{' '}
            <button type="button" className="linklike" onClick={() => input.current?.click()}>
              выберите файлы
            </button>
            <input
              ref={input}
              type="file"
              multiple
              hidden
              accept={ACCEPT_ATTRIBUTE}
              aria-label="Выбрать файлы технического задания"
              onChange={(e) => {
                if (e.target.files?.length) audit.addFiles(e.target.files)
                e.target.value = ''
              }}
            />
          </div>

          <div>
            {audit.documents.length > 0 ? (
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px' }} aria-label="Загруженные документы">
                {audit.documents.map((d) => (
                  <li key={d.localId} className="file-row" data-state={d.state}>
                    <span className="ficon">{fileTypeLabel(d.file.name)}</span>
                    <span className="grow">
                      <span className="name">{d.file.name}</span>
                      <span className="small muted">
                        {formatBytes(d.file.size)} ·{' '}
                        {d.state === 'uploading' && 'загрузка…'}
                        {d.state === 'ready' && (
                          <span className="text-ok">
                            загружен{d.meta?.page_count ? `, ${d.meta.page_count} стр.` : ''}
                          </span>
                        )}
                        {d.state === 'error' && <span className="text-bad" role="alert">{d.error}</span>}
                      </span>
                      {d.meta?.warnings?.map((w) => (
                        <span key={w} className="small text-warn" style={{ display: 'block' }}>{w}</span>
                      ))}
                    </span>
                    {d.state === 'error' && (
                      <button type="button" className="icon-btn" onClick={() => audit.retryDocument(d.localId)} aria-label={`Повторить загрузку ${d.file.name}`}>
                        <Icon name="retry" size={16} />
                      </button>
                    )}
                    <button type="button" className="icon-btn" onClick={() => audit.removeDocument(d.localId)} aria-label={`Убрать ${d.file.name}`}>
                      <Icon name="x" size={16} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted small" style={{ margin: '0 0 16px' }}>Файлы ещё не выбраны.</p>
            )}

            <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
              <legend className="small muted" style={{ marginBottom: 8, fontWeight: 600 }}>Режим анализа</legend>
              <div className="mode-options">
                <label className="mode-option">
                  <input type="radio" name="mode" checked={audit.mode === 'offline'} onChange={() => audit.setMode('offline')} />
                  <span>
                    <b>Офлайн</b>
                    <span className="small muted" style={{ display: 'block' }}>Локальные формальные проверки, без отправки текста</span>
                  </span>
                </label>
                <label className="mode-option">
                  <input type="radio" name="mode" disabled={publicDemo} checked={audit.mode === 'live'} onChange={() => audit.setMode('live')} />
                  <span>
                    <b>DeepSeek</b>
                    <span className="small muted" style={{ display: 'block' }}>{publicDemo ? publicModeNotice : 'Семантический анализ, нужен ключ на сервере'}</span>
                  </span>
                </label>
              </div>
              {audit.mode === 'live' && (
                <label className="consent">
                  <input type="checkbox" checked={audit.consent} onChange={(e) => audit.setConsent(e.target.checked)} />
                  <span>
                    Разрешаю отправить текст документов во внешний сервис DeepSeek для анализа. Запросы расходуют квоту владельца ключа.
                  </span>
                </label>
              )}
            </fieldset>

            {audit.error && (
              <div className="notice notice-error" role="alert" style={{ marginTop: 12 }}>
                {audit.error}
              </div>
            )}

            <button type="button" className="btn btn-primary" style={{ width: '100%', marginTop: 16, padding: '12px 16px' }} disabled={!canStart || audit.starting} aria-describedby={canStart ? undefined : 'start-help'} onClick={() => void audit.start()}>
              Начать анализ <Icon name="arrow" size={16} />
            </button>
            {!canStart && (
              <p className="helper" id="start-help">
                {uploading
                  ? 'Дождитесь окончания загрузки файлов.'
                  : liveBlocked
                    ? 'Для режима DeepSeek требуется согласие на отправку текста.'
                    : 'Добавьте хотя бы один документ PDF, Markdown или TXT.'}
              </p>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
