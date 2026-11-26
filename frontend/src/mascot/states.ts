// SPEC 4.1/4.2 state table, ported 1:1 from references/spec-source/prototype.js.
import type { EventStage } from '../api/types'

export const MASCOT_STATES = [
  'idle',
  'greeting',
  'upload',
  'extract',
  'thinking',
  'critical',
  'verify',
  'report',
  'success',
  'error',
  'attachment',
  'reading',
  'compare',
] as const

export type MascotState = (typeof MASCOT_STATES)[number]

const neutral = 'M74 105V109H86V105'
const happy = 'M72 103V110H88V103'
const sad = 'M73 112V106H87V112'
const focus = 'M74 106H86'
const surprise = 'M76 103H84V112H76Z'

export interface MascotLook {
  led: string
  eye: string
  label: string
  /** Eye height in viewBox units; eyes are centred on y=92. */
  eyeHeight: number
  mouth: string
  brows: string
}

export const LOOKS: Record<MascotState, MascotLook> = {
  idle: { led: '#facc15', eye: '#b4faff', label: 'Готов помочь', eyeHeight: 16, mouth: neutral, brows: '' },
  greeting: { led: '#facc15', eye: '#b4faff', label: 'Привет!', eyeHeight: 10, mouth: happy, brows: '' },
  upload: { led: '#38bdf8', eye: '#a5f3fc', label: 'Документ получен', eyeHeight: 12, mouth: happy, brows: '' },
  extract: { led: '#38bdf8', eye: '#a5f3fc', label: 'Извлекаю требования', eyeHeight: 12, mouth: focus, brows: '' },
  thinking: { led: '#a78bfa', eye: '#ddd6fe', label: 'Анализирую...', eyeHeight: 8, mouth: focus, brows: 'M55 79H68M91 79H104' },
  critical: { led: '#f59e0b', eye: '#fde68a', label: 'Противоречие!', eyeHeight: 20, mouth: surprise, brows: 'M55 78L68 75M91 75L104 78' },
  verify: { led: '#22d3ee', eye: '#a5f3fc', label: 'Проверяю доказательства', eyeHeight: 10, mouth: focus, brows: '' },
  report: { led: '#818cf8', eye: '#e0e7ff', label: 'Формирую отчёт', eyeHeight: 14, mouth: neutral, brows: '' },
  success: { led: '#22c55e', eye: '#bbf7d0', label: 'Отчёт готов!', eyeHeight: 10, mouth: happy, brows: '' },
  error: { led: '#ef4444', eye: '#fca5a5', label: 'Ошибка выполнения', eyeHeight: 13, mouth: sad, brows: 'M55 80L68 84M91 84L104 80' },
  attachment: { led: '#facc15', eye: '#b4faff', label: 'Файл прикреплён', eyeHeight: 12, mouth: happy, brows: '' },
  reading: { led: '#38bdf8', eye: '#a5f3fc', label: 'Читаю вложение', eyeHeight: 10, mouth: focus, brows: '' },
  compare: { led: '#a78bfa', eye: '#ddd6fe', label: 'Сравниваю документы', eyeHeight: 10, mouth: focus, brows: '' },
}

/** Russian names used by the accessible status and tests (order matches the prototype controls). */
export const STATE_NAMES: Record<MascotState, string> = {
  idle: 'Ожидание',
  greeting: 'Приветствие',
  upload: 'Документ получен',
  extract: 'Извлечение',
  thinking: 'Анализ',
  critical: 'Противоречие',
  verify: 'Проверка доказательств',
  report: 'Формирование отчёта',
  success: 'Успех',
  error: 'Ошибка',
  attachment: 'Вложение получено',
  reading: 'Чтение вложения',
  compare: 'Сравнение документов',
}

/**
 * Backend event stage → mascot state. Only real `Event.stage` values drive the mascot
 * (contracts/Event.schema.json); the UI never fabricates progress.
 */
export const STAGE_TO_STATE: Record<EventStage, MascotState> = {
  document_received: 'upload',
  extracting: 'extract',
  validating_individual: 'thinking',
  validating_global: 'thinking',
  contradiction_detected: 'critical',
  verifying_evidence: 'verify',
  generating_report: 'report',
  completed: 'success',
  failed: 'error',
  attachment_received: 'attachment',
  attachment_reading: 'reading',
  comparing_documents: 'compare',
  copilot_thinking: 'thinking',
  copilot_response_completed: 'idle',
}

/**
 * Dramatic states play a short, finite motion and then settle into the idle float
 * while keeping their colour and face (SPEC 4.2: "briefly play and settle").
 * Work-in-progress states loop while the backend reports that stage.
 */
export const DRAMATIC: ReadonlySet<MascotState> = new Set(['greeting', 'upload', 'critical', 'success', 'error', 'attachment'])

/** Minimum time each real event is shown so fast offline runs remain legible. */
export const EVENT_DWELL_MS = 650
