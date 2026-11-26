import type { AnalysisMode } from '../api/types'
import { Icon } from './Icons'

/** Always distinguishes offline deterministic checks from live DeepSeek analysis. */
export function ModeBadge({ mode, model }: { mode: AnalysisMode; model?: string }) {
  if (mode === 'live') {
    return (
      <span className="badge badge-live" title="Семантический анализ DeepSeek">
        <Icon name="sparkle" size={13} /> DeepSeek{model ? ` · ${model}` : ''}
      </span>
    )
  }
  return (
    <span className="badge badge-offline" title="Локальные детерминированные проверки без языковой модели">
      <Icon name="offline" size={13} /> Офлайн · без модели
    </span>
  )
}

export function OfflineNotice() {
  return (
    <div className="notice notice-offline" role="note">
      <Icon name="info" size={18} />
      <span>
        <b>Офлайн-режим.</b> Выполнены только локальные формальные проверки (структура, идентификаторы, ссылки, заглушки). Семантическая
        проверка DeepSeek не запускалась, поэтому покрытие неполное и вердикт может быть не определён.
      </span>
    </div>
  )
}
