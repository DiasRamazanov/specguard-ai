import { useEffect, useRef, useState } from 'react'
import { ApiError, type SpecGuardClient } from '../api/client'
import type { SourceBlock, SourceLocation } from '../api/types'
import { locationLabel } from './Evidence'
import { Icon } from './Icons'

export interface SourceTarget {
  location: SourceLocation
  quote?: string | null
}

interface Props {
  client: SpecGuardClient
  auditId: string
  target: SourceTarget
  filenames: Record<string, string>
  onClose: () => void
}

function highlight(text: string, quote?: string | null) {
  if (!quote) return text
  const i = text.indexOf(quote)
  if (i < 0) return text
  return (
    <>
      {text.slice(0, i)}
      <mark>{quote}</mark>
      {text.slice(i + quote.length)}
    </>
  )
}

/** Opens the cited source block via GET /audits/{id}/sources/{document_id}/{block_id}. */
export function SourceDrawer({ client, auditId, target, filenames, onClose }: Props) {
  const [block, setBlock] = useState<SourceBlock | null>(null)
  const [error, setError] = useState<string | null>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    let alive = true
    setBlock(null)
    setError(null)
    client
      .source(auditId, target.location.document_id, target.location.block_id)
      .then((b) => alive && setBlock(b))
      .catch((e) => alive && setError(e instanceof ApiError ? e.detail : 'Не удалось открыть источник.'))
    return () => {
      alive = false
    }
  }, [auditId, client, target.location.block_id, target.location.document_id])

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [onClose])

  return (
    <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="drawer" role="dialog" aria-modal="true" aria-label="Первоисточник">
        <div className="detail-head">
          <h2>Первоисточник</h2>
          <button ref={closeRef} type="button" className="icon-btn" onClick={onClose} aria-label="Закрыть источник">
            <Icon name="x" />
          </button>
        </div>
        <div className="detail-meta">
          <Icon name="doc" size={14} />
          {locationLabel(target.location, filenames[target.location.document_id])}
          <span className="mono">{target.location.block_id}</span>
        </div>
        {error && <div className="notice notice-error">{error}</div>}
        {!block && !error && <p className="muted">Загрузка фрагмента…</p>}
        {block && <div className="source-text">{highlight(block.text, target.quote)}</div>}
      </div>
    </div>
  )
}
