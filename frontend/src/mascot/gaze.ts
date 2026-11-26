// 70% gaze tracking, adapted from references/spec-source/spec-gaze.ts.
// Pointer coordinates are used locally only and never sent to the backend.

/** 70% sensitivity → max displacement 10.5 × 6.3 units in the 160-unit viewBox. */
export const GAZE_SENSITIVITY = 0.7
export const GAZE_MAX_X = 15 * GAZE_SENSITIVITY // 10.5
export const GAZE_MAX_Y = 9 * GAZE_SENSITIVITY // 6.3
const EYE_CENTRE = { x: 80, y: 92 }

/** Bounded gaze offset for a pointer at (px, py) in viewBox coordinates. */
export function gazeOffset(px: number, py: number): { x: number; y: number } {
  const dx = px - EYE_CENTRE.x
  const dy = py - EYE_CENTRE.y
  const d = Math.hypot(dx, dy)
  const n = Math.max(d, 1)
  const ease = 1 - Math.exp(-d / 25)
  return { x: (dx / n) * GAZE_MAX_X * ease, y: (dy / n) * GAZE_MAX_Y * ease }
}

export function installGaze(root: HTMLElement, gaze: SVGGElement, motionAllowed: () => boolean): () => void {
  let x = 0
  let y = 0
  let tx = 0
  let ty = 0
  let raf = 0

  const frame = () => {
    x += (tx - x) * 0.55
    y += (ty - y) * 0.55
    gaze.setAttribute('transform', `translate(${x.toFixed(2)} ${y.toFixed(2)})`)
    raf = Math.abs(tx - x) + Math.abs(ty - y) > 0.03 ? requestAnimationFrame(frame) : 0
  }
  const target = (a: number, b: number) => {
    tx = a
    ty = b
    if (!raf) raf = requestAnimationFrame(frame)
  }
  const move = (e: PointerEvent) => {
    if (!motionAllowed()) return
    const parent = gaze.parentNode as SVGGraphicsElement | null
    const m = parent?.getScreenCTM?.()
    if (!m) return
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse())
    const o = gazeOffset(p.x, p.y)
    target(o.x, o.y)
  }
  const leave = () => target(0, 0)

  root.addEventListener('pointermove', move)
  root.addEventListener('pointerleave', leave)
  return () => {
    root.removeEventListener('pointermove', move)
    root.removeEventListener('pointerleave', leave)
    cancelAnimationFrame(raf)
    gaze.setAttribute('transform', 'translate(0 0)')
  }
}
