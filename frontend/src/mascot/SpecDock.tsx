// SPEC permanently docked at the bottom of the workspace sidebar (SPEC 4.2).
// Single click: acknowledgement. Double click: activation bounce + toggle Copilot.
// Keyboard Enter/Space toggles (click with detail 0). Explicit button for mobile.
import { forwardRef, useState } from 'react'
import { Icon } from '../components/Icons'
import { SpecMascot, type Gesture } from './SpecMascot'
import { LOOKS, type MascotState } from './states'

interface Props {
  state: MascotState
  open: boolean
  onToggle: (open: boolean) => void
  gazeRoot: HTMLElement | null
  motion: boolean
  onMotionChange: (v: boolean) => void
}

const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches

export const SpecDock = forwardRef<HTMLButtonElement, Props>(function SpecDock({ state, open, onToggle, gazeRoot, motion, onMotionChange }, ref) {
  const [gesture, setGesture] = useState<Gesture>(null)
  const [gestureKey, setGestureKey] = useState(0)
  const motionAllowed = () => motion && !reducedMotion()

  const play = (g: Exclude<Gesture, null>) => {
    if (!motionAllowed()) return
    setGesture(g)
    setGestureKey((k) => k + 1)
  }
  const toggle = () => {
    const next = !open
    if (next) play('wake')
    onToggle(next)
  }

  return (
    <div className="dock" data-testid="spec-dock">
      <button
        ref={ref}
        type="button"
        className="dock-trigger"
        aria-expanded={open}
        aria-controls="spec-copilot"
        aria-label="SPEC — дважды щёлкните или нажмите Enter, чтобы открыть Copilot"
        title="Двойной щелчок — открыть SPEC Copilot"
        onClick={(e) => {
          if (e.detail === 0) toggle()
          else if (e.detail === 1) play('ack')
        }}
        onDoubleClick={(e) => {
          e.preventDefault()
          toggle()
        }}
      >
        <SpecMascot
          state={state}
          gesture={gesture}
          gestureKey={gestureKey}
          onGestureEnd={() => setGesture(null)}
          gazeRoot={gazeRoot}
          motionAllowed={motionAllowed}
        />
      </button>
      <span className="dock-status" role="status" aria-live="polite" data-testid="spec-status" data-state={state}>
        {LOOKS[state].label}
      </span>
      <p className="dock-hint">Двойной щелчок — SPEC Copilot</p>
      <button type="button" className="btn btn-secondary btn-sm dock-open" onClick={toggle} aria-expanded={open} aria-controls="spec-copilot">
        <Icon name="chat" size={15} /> {open ? 'Закрыть' : 'Copilot'}
      </button>
      <label className="motion-toggle">
        <input type="checkbox" checked={motion} onChange={(e) => onMotionChange(e.target.checked)} /> Анимация SPEC
      </label>
    </div>
  )
})
