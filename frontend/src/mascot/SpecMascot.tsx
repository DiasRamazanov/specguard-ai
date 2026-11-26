// SPEC mascot. Artwork geometry is preserved from references/spec-source/spec-mascot.svg.
// Independent nested layers (SPEC 4.2):
//   .spec-gesture  – one-shot click/double-click gestures (wake, ack)
//   .spec-body     – state body motion (float, nod, tilt, recoil, shake)
//   .led / .spec-fx – dynamic LED colour and state effect icons
//   .gaze          – 70% pointer gaze (JS transform)
//   .gaze-auto     – autonomous alternating gaze while comparing documents
//   .blink         – expression: eyes, brows, blink
import { useEffect, useId, useRef } from 'react'
import { LOOKS, type MascotState } from './states'
import { installGaze } from './gaze'
import './mascot.css'

export type Gesture = 'wake' | 'ack' | null

interface Props {
  state: MascotState
  gesture?: Gesture
  /** Changes on each gesture so a repeated gesture restarts. */
  gestureKey?: number
  onGestureEnd?: () => void
  /** Element whose pointer movement the eyes follow; omit for a static avatar. */
  gazeRoot?: HTMLElement | null
  motionAllowed?: () => boolean
  className?: string
  title?: string
  /** Purely decorative illustration: hidden from assistive technology. */
  decorative?: boolean
}

export function SpecMascot({ state, gesture = null, gestureKey = 0, onGestureEnd, gazeRoot, motionAllowed, className, title, decorative }: Props) {
  const look = LOOKS[state]
  const clip = `spec-screen-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  const gazeRef = useRef<SVGGElement>(null)
  const gestureRef = useRef<SVGGElement>(null)
  const bodyRef = useRef<SVGGElement>(null)
  const allowed = useRef(motionAllowed)
  allowed.current = motionAllowed

  useEffect(() => {
    if (!gazeRoot || !gazeRef.current) return
    return installGaze(gazeRoot, gazeRef.current, () => allowed.current?.() ?? true)
  }, [gazeRoot])

  // Restart the gesture animation on every new gesture key.
  useEffect(() => {
    const g = gestureRef.current
    if (!g || !gesture) return
    g.classList.remove('wake', 'ack')
    void g.getBoundingClientRect()
    g.classList.add(gesture)
  }, [gesture, gestureKey])

  // Restart body/effect animations on each state change (prototype: animation='none' + reflow).
  // The layer is not remounted, so the gaze listener stays bound.
  useEffect(() => {
    const body = bodyRef.current
    if (!body) return
    const layers = [body, ...Array.from(body.querySelectorAll<SVGElement>('.spec-fx > g, .scan, .gaze-auto'))]
    layers.forEach((el) => (el.style.animation = 'none'))
    void body.getBoundingClientRect()
    layers.forEach((el) => (el.style.animation = ''))
  }, [state])

  const eyeY = 92 - look.eyeHeight / 2

  return (
    <svg
      className={`robot${className ? ` ${className}` : ''}`}
      viewBox="0 0 160 150"
      shapeRendering="crispEdges"
      data-state={state}
      style={{ ['--led' as string]: look.led, ['--eye' as string]: look.eye }}
      role={decorative ? undefined : 'img'}
      aria-hidden={decorative || undefined}
      aria-label={decorative ? undefined : (title ?? `SPEC: ${look.label}`)}
    >
      <g
        ref={gestureRef}
        className="spec-gesture"
        onAnimationEnd={(e) => {
          if (e.animationName === 'spec-activate' || e.animationName === 'spec-ack') {
            e.currentTarget.classList.remove('wake', 'ack')
            onGestureEnd?.()
          }
        }}
      >
        <g className="spec-body" ref={bodyRef}>
          {/* Antenna: document with checkmark (replaces the reference chart antenna). */}
          <path d="M72 43V28H85V43Z" fill="#7aa7c8" stroke="#11152d" strokeWidth="4" />
          <path d="M58 6H94V12H100V31H94V36H58Z" fill="#fff" stroke="#11152d" strokeWidth="4" />
          <path d="M65 13H89V17H65ZM65 22H77V25H65Z" fill="#a8b6d6" />
          <path d="M79 25L85 31L97 18" stroke="#11152d" strokeWidth="6" fill="none" />
          <path d="M79 25L85 31L97 18" stroke="#facc15" strokeWidth="3" fill="none" />
          {/* Ears */}
          <path d="M24 66H12V73H7V103H12V112H28ZM136 66H148V73H153V103H148V112H132Z" fill="#e8a11b" stroke="#11152d" strokeWidth="5" />
          {/* Helmet */}
          <path
            d="M43 37H117V43H130V53H139V65H145V120H138V132H127V139H33V132H22V120H15V65H21V53H30V43H43Z"
            fill="#f8fdff"
            stroke="#101329"
            strokeWidth="5"
          />
          <path d="M129 51H137V64H142V119H134V130H124V137H37V131H122V124H130V115H135V68H129Z" fill="#85b5d6" />
          {/* Permanent gold shell */}
          <path
            d="M43 52H117V58H127V69H133V116H126V125H116V131H44V125H34V116H27V69H33V58H43Z"
            fill="#f9c72e"
            stroke="#68340e"
            strokeWidth="4"
          />
          <path d="M43 55H116V61H125V70H130V79H124V68H115V62H44V67H35V78H30V68H36V60H43Z" fill="#fff17c" />
          {/* Dynamic LED ring */}
          <path className="led" fill="var(--led)" d="M43 65H117V71H123V113H117V121H43V115H37V73H43Z" />
          {/* Navy face screen */}
          <path d="M47 70H113V75H118V109H112V116H48V110H42V76H47Z" fill="#07142d" stroke="#101329" strokeWidth="3" />
          <path d="M48 76H110V88L48 96Z" fill="#24445b" opacity=".7" />
          <path d="M48 84V78H54V75H64V79H55V84Z" fill="#89f5ff" opacity=".65" />
          <clipPath id={clip}>
            <rect x="45" y="75" width="70" height="34" rx="4" />
          </clipPath>
          <g clipPath={`url(#${clip})`}>
            <g className="gaze" ref={gazeRef}>
              <g className="gaze-auto">
                <g className="blink" fill="var(--eye)">
                  <rect className="eyes le" x="56" y={eyeY} width="11" height={look.eyeHeight} rx="1" />
                  <rect className="eyes re" x="92" y={eyeY} width="11" height={look.eyeHeight} rx="1" />
                  <path className="faceline brows" d={look.brows} stroke="var(--eye)" strokeWidth="3" fill="none" />
                </g>
              </g>
            </g>
            <path className="scan" d="M44 86H116" stroke="#67e8f9" strokeWidth="2" />
          </g>
          <path className="faceline mouth" d={look.mouth} stroke="var(--eye)" strokeWidth="3" fill="none" />
          {/* State effects */}
          <g className="spec-fx">
            <g className="alert">
              <path d="M133 4L155 39H111Z" fill="var(--led)" stroke="#17152d" strokeWidth="3" />
              <path d="M133 15V25M133 29V33" stroke="#fff" strokeWidth="4" />
            </g>
            <g className="paper">
              <path d="M118 4H143L153 14V45H118Z" fill="#fff" stroke="#29224a" strokeWidth="3" />
              <path d="M143 4V15H153M124 24H146M124 31H146M124 38H139" stroke="#8a78c5" strokeWidth="2" fill="none" />
            </g>
            <g className="paper2">
              <path d="M4 7H28L36 15V44H4Z" fill="#fff" stroke="#29224a" strokeWidth="3" />
              <path d="M10 23H29M10 30H29M10 37H24" stroke="#8a78c5" strokeWidth="2" />
            </g>
            <g className="glass">
              <circle cx="132" cy="24" r="15" fill="#c6f8ff" stroke="#18203c" strokeWidth="4" />
              <path d="M143 35L155 47" stroke="#18203c" strokeWidth="6" />
            </g>
            <g className="dots" fill="#a78bfa">
              <rect x="116" y="12" width="7" height="7" />
              <rect x="130" y="12" width="7" height="7" />
              <rect x="144" y="12" width="7" height="7" />
            </g>
            <g className="spark" fill="#22c55e">
              <path d="M13 20H19V27H26V33H19V40H13V33H6V27H13Z" />
              <path d="M134 7H140V14H147V20H140V27H134V20H127V14H134Z" />
            </g>
          </g>
        </g>
      </g>
    </svg>
  )
}
