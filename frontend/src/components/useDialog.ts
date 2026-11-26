// Modal dialog behaviour: moves focus in, traps Tab inside, closes on Escape
// (without letting Escape reach the Copilot handler), and restores focus to the opener.
import { useEffect, useRef } from 'react'

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

export function useDialog<T extends HTMLElement>(onClose: () => void) {
  const ref = useRef<T>(null)
  const close = useRef(onClose)
  close.current = onClose

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null
    const root = ref.current
    const focusables = () => (root ? Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)) : [])
    ;(root?.querySelector<HTMLElement>('[data-autofocus]') ?? focusables()[0] ?? root)?.focus()

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        e.preventDefault()
        close.current()
        return
      }
      if (e.key !== 'Tab' || !root) return
      const items = focusables()
      if (!items.length) return
      const first = items[0]
      const last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => {
      window.removeEventListener('keydown', onKey, true)
      if (opener && document.contains(opener)) opener.focus()
    }
  }, [])

  return ref
}
