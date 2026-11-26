// Dev-only harness: renders the production SpecMascot in each of the 13 approved states
// so they can be inspected and verified in a real browser (e2e/spec-states.e2e.ts).
// It is not reachable from the app and is not included in the production build.
import { StrictMode, useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/app.css'
import { SpecMascot } from '../mascot/SpecMascot'
import { LOOKS, MASCOT_STATES, STATE_NAMES, type MascotState } from '../mascot/states'

function Harness() {
  const [root, setRoot] = useState<HTMLElement | null>(null)
  const [focus, setFocus] = useState<MascotState>('idle')
  return (
    <div ref={setRoot} style={{ padding: 24, minHeight: '100vh' }}>
      <h1 style={{ marginBottom: 6 }}>SPEC — 13 состояний</h1>
      <p className="muted small" style={{ marginBottom: 18 }}>
        Проверочный стенд для разработки. Состояния в приложении меняются только по событиям сервера.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 14 }}>
        {MASCOT_STATES.map((s) => (
          <figure
            key={s}
            className="card"
            data-testid={`state-${s}`}
            style={{ margin: 0, textAlign: 'center', padding: '18px 10px 12px', outline: focus === s ? '2px solid var(--primary)' : undefined }}
            onMouseEnter={() => setFocus(s)}
          >
            <div style={{ height: 130, display: 'grid', placeItems: 'center' }}>
              <SpecMascot state={s} gazeRoot={focus === s ? root : null} />
            </div>
            <figcaption style={{ marginTop: 8 }}>
              <b className="small">{STATE_NAMES[s]}</b>
              <span className="small muted" style={{ display: 'block' }}>
                <span className="mono">{s}</span> · {LOOKS[s].label}
              </span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Harness />
  </StrictMode>,
)
