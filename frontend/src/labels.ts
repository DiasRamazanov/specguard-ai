// Russian display labels for contract enums. Values come from contracts/openapi.json.
import type { EventStage, Finding, Readiness, RequirementAssessment, Severity } from './api/types'

export const STAGE_LABELS: Record<EventStage, string> = {
  document_received: 'Документ получен',
  extracting: 'Извлечение требований',
  validating_individual: 'Проверка отдельных требований',
  validating_global: 'Проверка связей и согласованности',
  contradiction_detected: 'Обнаружено противоречие',
  verifying_evidence: 'Проверка доказательств',
  generating_report: 'Формирование отчёта',
  completed: 'Аудит завершён',
  failed: 'Аудит завершился ошибкой',
  attachment_received: 'Вложение получено',
  attachment_reading: 'Чтение вложения',
  comparing_documents: 'Сравнение документов',
  copilot_thinking: 'SPEC анализирует вопрос',
  copilot_response_completed: 'Ответ SPEC готов',
}

/** Audit pipeline stages in display order (copilot/attachment stages are shown in the Copilot). */
export const PIPELINE: { stage: EventStage; label: string }[] = [
  { stage: 'document_received', label: 'Получение документа' },
  { stage: 'extracting', label: 'Извлечение требований' },
  { stage: 'validating_individual', label: 'Проверка требований' },
  { stage: 'validating_global', label: 'Поиск противоречий и связей' },
  { stage: 'verifying_evidence', label: 'Проверка доказательств' },
  { stage: 'generating_report', label: 'Формирование отчёта' },
]

export const SEVERITY_LABELS: Record<Severity, string> = {
  critical: 'Критическое',
  major: 'Высокое',
  minor: 'Среднее',
  informational: 'Информация',
}

export const SEVERITY_ORDER: Severity[] = ['critical', 'major', 'minor', 'informational']

export const FINDING_STATUS_LABELS: Record<Finding['status'], string> = {
  confirmed: 'Подтверждено',
  requires_clarification: 'Требует уточнения',
  context_dependent: 'Зависит от контекста',
}

export const VERDICT_LABELS: Record<Readiness['verdict'], string> = {
  ready: 'ТЗ готово к разработке',
  ready_with_conditions: 'Готово с условиями',
  requires_revision: 'Требуется доработка',
  unable_to_determine: 'Готовность не определена',
}

export const ASSESSMENT_LABELS: Record<RequirementAssessment['status'], string> = {
  complete: 'Проверено',
  incomplete: 'Проверено частично',
  offline: 'Только формальные проверки',
}

export const CRITERION_STATUS_LABELS: Record<string, string> = {
  valid: 'Соответствует',
  confirmed_defect: 'Дефект',
  requires_clarification: 'Требует уточнения',
  context_dependent: 'Зависит от контекста',
  insufficient_evidence: 'Недостаточно данных',
  not_applicable: 'Неприменимо',
}

export const CRITERION_LABELS: Record<string, string> = {
  completeness: 'Полнота',
  correctness: 'Корректность',
  unambiguity: 'Однозначность',
  unambiguous: 'Однозначность',
  consistency: 'Согласованность',
  verifiability: 'Проверяемость',
  testability: 'Тестируемость',
  traceability: 'Трассируемость',
  feasibility: 'Реализуемость',
  necessity: 'Необходимость',
  singularity: 'Единичность',
  conformity: 'Соответствие',
  appropriateness: 'Уместность',
}

export const criterionLabel = (c: string) => CRITERION_LABELS[c] ?? c

/** Mirrors specguard/core.py CONTRADICTIONS. */
export const CONTRADICTION_KINDS = new Set(['contradiction', 'conflict', 'противоречие'])
export const isContradiction = (f: Finding) => CONTRADICTION_KINDS.has(f.kind)

export const PURPOSE_LABELS = {
  context: 'Контекст',
  comparison: 'Сравнение',
  revision: 'Новая редакция',
} as const

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} Б`
  if (n < 1024 * 1024) return `${Math.ceil(n / 1024)} КБ`
  return `${(n / 1024 / 1024).toFixed(1)} МБ`
}

export function fileTypeLabel(name: string): string {
  const ext = name.split('.').pop()?.toUpperCase() ?? ''
  return ext === 'MARKDOWN' ? 'MD' : ext
}

export function shortId(id: string, keep = 8): string {
  const dash = id.indexOf('-')
  const prefix = dash > 0 && dash < 9 ? id.slice(0, dash + 1) : ''
  const rest = id.slice(prefix.length)
  return prefix + (rest.length > keep ? rest.slice(0, keep) : rest)
}
