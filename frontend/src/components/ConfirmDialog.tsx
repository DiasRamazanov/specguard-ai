import { useId } from 'react'
import { useDialog } from './useDialog'

interface Props {
  title: string
  children: React.ReactNode
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

/** In-app confirmation (replaces window.confirm): labelled, focus-trapped, Escape cancels. */
export function ConfirmDialog({ title, children, confirmLabel, onConfirm, onCancel }: Props) {
  const ref = useDialog<HTMLDivElement>(onCancel)
  const titleId = useId()
  return (
    <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onCancel()}>
      <div ref={ref} className="drawer" role="alertdialog" aria-modal="true" aria-labelledby={titleId} style={{ width: 'min(480px, 100%)' }}>
        <h2 id={titleId} style={{ fontSize: 19, marginBottom: 8 }}>{title}</h2>
        <div className="muted">{children}</div>
        <div className="dialog-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel} data-autofocus>
            Отмена
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
