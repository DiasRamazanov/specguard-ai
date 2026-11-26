import type { Requirement } from '../api/types'
import { displaySummary } from '../views/shared'

const req = (original_id: string | null, summary: string): Requirement => ({
  requirement_id: 'req-x',
  document_id: 'doc-x',
  original_id,
  summary,
  kind: 'functional',
  evidence: [],
})

describe('displaySummary', () => {
  it('strips a list marker and the requirement\'s own ID with a delimiter', () => {
    expect(displaySummary(req('SG-602', '- SG-602: Размер пакета не более 20.'))).toBe('Размер пакета не более 20.')
    expect(displaySummary(req('REQ-1', 'REQ-1 — Текст'))).toBe('Текст')
    expect(displaySummary(req('REQ-1', 'REQ-1 – Текст'))).toBe('Текст')
    expect(displaySummary(req('REQ-1', 'REQ-1 - Текст'))).toBe('Текст')
    expect(displaySummary(req('REQ-1', '1. REQ-1: Текст'))).toBe('Текст')
  })

  describe('overlapping IDs (regression: REQ-1 vs REQ-10)', () => {
    const cases: [string, string, string][] = [
      ['REQ-1', 'REQ-10: Десятое требование', 'REQ-10: Десятое требование'],
      ['REQ-1', 'REQ-100: Сотое требование', 'REQ-100: Сотое требование'],
      ['REQ-10', 'REQ-100: Сотое требование', 'REQ-100: Сотое требование'],
      ['REQ-10', 'REQ-1: Первое требование', 'REQ-1: Первое требование'],
      ['REQ-1', 'REQ-1: Первое требование', 'Первое требование'],
      ['REQ-10', 'REQ-10: Десятое требование', 'Десятое требование'],
      ['REQ-100', 'REQ-100: Сотое требование', 'Сотое требование'],
      ['REQ-1', '- REQ-10: Десятое', 'REQ-10: Десятое'],
      ['REQ-1', 'REQ-1-A: Подпункт', 'REQ-1-A: Подпункт'],
      ['REQ-1', 'REQ-1.2: Подпункт', 'REQ-1.2: Подпункт'],
    ]
    it.each(cases)('ID %s, summary "%s" → "%s"', (id, summary, expected) => {
      expect(displaySummary(req(id, summary))).toBe(expected)
    })
  })

  it('leaves text unchanged when there is no delimiter or nothing after the ID', () => {
    expect(displaySummary(req('REQ-1', 'REQ-1 описывает вход'))).toBe('REQ-1 описывает вход')
    expect(displaySummary(req('REQ-1', 'REQ-1:'))).toBe('REQ-1:')
    expect(displaySummary(req(null, 'REQ-1: Текст'))).toBe('REQ-1: Текст')
  })

  it('treats regex characters in IDs literally', () => {
    expect(displaySummary(req('A.1', 'AB1: Текст'))).toBe('AB1: Текст')
    expect(displaySummary(req('A.1', 'A.1: Текст'))).toBe('Текст')
    expect(displaySummary(req('Ф-3(б)', 'Ф-3(б): Текст'))).toBe('Текст')
  })
})
