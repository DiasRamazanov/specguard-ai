// Drives SPEC from real backend events. Each unseen event is queued and shown for at
// least EVENT_DWELL_MS so fast offline runs stay legible; the last state persists.
import { useCallback, useEffect, useRef, useState } from 'react'
import type { AuditEvent } from '../api/types'
import { EVENT_DWELL_MS, STAGE_TO_STATE, type MascotState } from './states'

export interface MascotDriver {
  state: MascotState
  /** Enqueue events of one audit; already-seen sequence numbers are ignored. */
  pushEvents: (auditId: string, events: AuditEvent[]) => void
  /** Enqueue a state caused by a real client-side outcome (e.g. API error, session start). */
  signal: (state: MascotState) => void
  /** Forget seen events (new audit / new session). */
  reset: () => void
}

export function useMascotDriver(initial: MascotState = 'idle', dwellMs = EVENT_DWELL_MS): MascotDriver {
  const [state, setState] = useState<MascotState>(initial)
  const queue = useRef<MascotState[]>([])
  const seen = useRef(new Map<string, number>())
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const pump = useCallback(() => {
    if (timer.current) return
    const next = queue.current.shift()
    if (!next) return
    setState(next)
    timer.current = setTimeout(() => {
      timer.current = null
      pump()
    }, dwellMs)
  }, [dwellMs])

  const pushEvents = useCallback(
    (auditId: string, events: AuditEvent[]) => {
      const last = seen.current.get(auditId) ?? 0
      const fresh = events.filter((e) => e.sequence > last).sort((a, b) => a.sequence - b.sequence)
      if (!fresh.length) return
      seen.current.set(auditId, fresh[fresh.length - 1].sequence)
      queue.current.push(...fresh.map((e) => STAGE_TO_STATE[e.stage]))
      pump()
    },
    [pump],
  )

  const signal = useCallback(
    (s: MascotState) => {
      queue.current.push(s)
      pump()
    },
    [pump],
  )

  const reset = useCallback(() => {
    seen.current.clear()
  }, [])

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current)
    },
    [],
  )

  return { state, pushEvents, signal, reset }
}
