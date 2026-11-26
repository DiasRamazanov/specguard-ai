import { act, render, renderHook } from '@testing-library/react'
import openapi from '../../../contracts/openapi.json'
import type { AuditEvent, EventStage } from '../api/types'
import { SpecMascot } from '../mascot/SpecMascot'
import { GAZE_MAX_X, GAZE_MAX_Y, GAZE_SENSITIVITY, gazeOffset } from '../mascot/gaze'
import { DRAMATIC, LOOKS, MASCOT_STATES, STAGE_TO_STATE } from '../mascot/states'
import { useMascotDriver } from '../mascot/useMascotDriver'

describe('SPEC state table', () => {
  it('defines exactly the 13 approved states', () => {
    expect(MASCOT_STATES).toHaveLength(13)
    for (const s of MASCOT_STATES) expect(LOOKS[s]).toBeDefined()
  })

  it('maps every backend Event.stage from the contract to a mascot state', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const stages = (openapi as any).components.schemas.Event.properties.stage.enum as EventStage[]
    expect(stages.length).toBeGreaterThan(0)
    for (const stage of stages) expect(MASCOT_STATES).toContain(STAGE_TO_STATE[stage])
  })

  it('uses the approved colours for key states', () => {
    expect(LOOKS.idle.led).toBe('#facc15')
    expect(LOOKS.error.led).toBe('#ef4444')
    expect(LOOKS.success.led).toBe('#22c55e')
    expect(LOOKS.critical.led).toBe('#f59e0b')
    expect(LOOKS.verify.led).toBe('#22d3ee')
    expect(LOOKS.report.led).toBe('#818cf8')
  })

  it('treats error/success/contradiction as brief dramatic states', () => {
    for (const s of ['error', 'success', 'critical', 'greeting'] as const) expect(DRAMATIC.has(s)).toBe(true)
    for (const s of ['extract', 'thinking', 'verify'] as const) expect(DRAMATIC.has(s)).toBe(false)
  })
})

describe('70% gaze', () => {
  it('is bounded to 10.5 × 6.3 viewBox units', () => {
    expect(GAZE_SENSITIVITY).toBe(0.7)
    expect(GAZE_MAX_X).toBeCloseTo(10.5)
    expect(GAZE_MAX_Y).toBeCloseTo(6.3)
    for (const [x, y] of [
      [10000, 92],
      [-10000, 92],
      [80, 10000],
      [80, -10000],
      [5000, 5000],
    ]) {
      const o = gazeOffset(x, y)
      expect(Math.abs(o.x)).toBeLessThanOrEqual(10.5 + 1e-9)
      expect(Math.abs(o.y)).toBeLessThanOrEqual(6.3 + 1e-9)
    }
    expect(gazeOffset(10000, 92).x).toBeGreaterThan(10.4)
  })

  it('is neutral at the eye centre', () => {
    const o = gazeOffset(80, 92)
    expect(Math.abs(o.x)).toBeLessThan(1e-9)
    expect(Math.abs(o.y)).toBeLessThan(1e-9)
  })
})

describe('SpecMascot', () => {
  it.each(MASCOT_STATES)('renders state %s with its LED colour and face', (state) => {
    const { container } = render(<SpecMascot state={state} />)
    const svg = container.querySelector('svg.robot') as SVGElement
    expect(svg.getAttribute('data-state')).toBe(state)
    expect(svg.style.getPropertyValue('--led')).toBe(LOOKS[state].led)
    const eye = container.querySelector('.le')!
    expect(eye.getAttribute('height')).toBe(String(LOOKS[state].eyeHeight))
    expect(Number(eye.getAttribute('y'))).toBe(92 - LOOKS[state].eyeHeight / 2)
    expect(container.querySelector('.mouth')!.getAttribute('d')).toBe(LOOKS[state].mouth)
  })

  it('keeps separate nested layers for gesture, body, gaze, expression and effects', () => {
    const { container } = render(<SpecMascot state="idle" />)
    expect(container.querySelector('.spec-gesture > .spec-body')).not.toBeNull()
    expect(container.querySelector('.spec-body .gaze > .gaze-auto > .blink')).not.toBeNull()
    expect(container.querySelector('.spec-body .spec-fx')).not.toBeNull()
    expect(container.querySelector('.led')).not.toBeNull()
  })

  it('keeps the permanent gold shell in every state', () => {
    for (const s of MASCOT_STATES) {
      const { container, unmount } = render(<SpecMascot state={s} />)
      expect(container.querySelector('path[fill="#f9c72e"]')).not.toBeNull()
      unmount()
    }
  })

  it('gives each instance a unique screen clip id', () => {
    const { container } = render(
      <>
        <SpecMascot state="idle" />
        <SpecMascot state="error" />
      </>,
    )
    const ids = [...container.querySelectorAll('clipPath')].map((c) => c.id)
    expect(new Set(ids).size).toBe(2)
  })
})

describe('useMascotDriver', () => {
  const ev = (sequence: number, stage: EventStage): AuditEvent => ({ sequence, stage, time: '2026-11-26T00:00:00Z', finding_id: null })

  it('plays only unseen real events in order, each for the dwell time', () => {
    vi.useFakeTimers()
    const { result } = renderHook(() => useMascotDriver('idle', 100))
    act(() => result.current.pushEvents('a', [ev(1, 'document_received'), ev(2, 'extracting')]))
    expect(result.current.state).toBe('upload')
    act(() => vi.advanceTimersByTime(100))
    expect(result.current.state).toBe('extract')
    // Re-polling the same events must not replay them.
    act(() => result.current.pushEvents('a', [ev(1, 'document_received'), ev(2, 'extracting'), ev(3, 'completed')]))
    act(() => vi.advanceTimersByTime(100))
    expect(result.current.state).toBe('success')
    act(() => vi.advanceTimersByTime(1000))
    expect(result.current.state).toBe('success')
    vi.useRealTimers()
  })

  it('maps failed to the error state', () => {
    const { result } = renderHook(() => useMascotDriver('idle', 10))
    act(() => result.current.pushEvents('b', [ev(1, 'failed')]))
    expect(result.current.state).toBe('error')
  })
})
