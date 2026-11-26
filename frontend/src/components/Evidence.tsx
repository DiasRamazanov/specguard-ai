import type { Evidence, SourceLocation } from '../api/types'
import { Icon } from './Icons'

export function locationLabel(loc: SourceLocation, filename?: string): string {
  const parts: string[] = []
  if (filename) parts.push(filename)
  if (loc.page != null) parts.push(`стр. ${loc.page}`)
  if (loc.line_start != null) {
    parts.push(loc.line_end != null && loc.line_end !== loc.line_start ? `строки ${loc.line_start}–${loc.line_end}` : `строка ${loc.line_start}`)
  }
  if (loc.section) parts.push(`§ ${loc.section}`)
  return parts.join(' · ')
}

interface Props {
  items: Evidence[]
  filenames: Record<string, string>
  onOpen: (loc: SourceLocation, quote?: string | null) => void
  empty?: string
}

/** Source citations. Quotes are rendered as text (never HTML) — documents are untrusted input. */
export function EvidenceList({ items, filenames, onOpen, empty = 'Цитаты отсутствуют.' }: Props) {
  if (!items.length) return <p className="muted small">{empty}</p>
  return (
    <div>
      {items.map((ev) =>
        ev.kind === 'quote' ? (
          <button
            key={ev.evidence_id}
            type="button"
            className="evidence"
            onClick={() => onOpen(ev.location, ev.quote)}
            aria-label={`Открыть источник: ${locationLabel(ev.location, filenames[ev.location.document_id])}`}
          >
            <span className="loc">
              <Icon name="doc" size={14} />
              {locationLabel(ev.location, filenames[ev.location.document_id])}
            </span>
            <q>{ev.quote}</q>
          </button>
        ) : (
          <div key={ev.evidence_id} className="evidence absence">
            <span className="loc">
              <Icon name="search" size={14} />
              Отсутствие · {locationLabel(ev.location, filenames[ev.location.document_id])}
            </span>
            <span>{ev.scope ?? 'Искомое положение в документе не найдено.'}</span>
          </div>
        ),
      )}
    </div>
  )
}
