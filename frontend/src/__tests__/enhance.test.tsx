import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import fixture from '../../../contracts/fixtures/mock-audit.json'
import { parseRoute, routeHash } from '../App'
import type { AuditResult } from '../api/types'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { FindingsView } from '../views/FindingsView'

const result = (fixture as { result: unknown }).result as AuditResult
const props = { result, filenames: {}, openSource: vi.fn(), askSpec: vi.fn(), requestRevision: vi.fn(), navigate: vi.fn() }

describe('deep-link routes', () => {
  it('round-trips view and id', () => {
    expect(routeHash('findings', 'finding-1')).toBe('#/findings/finding-1')
    expect(parseRoute('#/findings/finding-1')).toEqual({ view: 'findings', id: 'finding-1' })
    expect(parseRoute('#/report')).toEqual({ view: 'report', id: undefined })
  })

  it('encodes ids safely and rejects unknown views', () => {
    const id = 'req/with space'
    expect(parseRoute(routeHash('requirements', id))).toEqual({ view: 'requirements', id })
    expect(parseRoute('#/admin')).toBeNull()
    expect(parseRoute('#main')).toBeNull()
    expect(parseRoute('')).toBeNull()
  })
})

describe('finding tabs (WAI-ARIA)', () => {
  it('links tabs to the panel and supports arrow / Home / End keys', async () => {
    render(<FindingsView {...props} selectedId={result.findings[0].finding_id} />)
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(4)
    const panel = screen.getByRole('tabpanel')
    expect(tabs[0]).toHaveAttribute('aria-controls', panel.id)
    expect(panel).toHaveAttribute('aria-labelledby', tabs[0].id)
    expect(tabs[0]).toHaveAttribute('tabindex', '0')
    expect(tabs[1]).toHaveAttribute('tabindex', '-1')

    tabs[0].focus()
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Влияние' })).toHaveAttribute('aria-selected', 'true')
    expect(document.activeElement).toBe(screen.getByRole('tab', { name: 'Влияние' }))
    await userEvent.keyboard('{End}')
    expect(screen.getByRole('tab', { name: 'Источник' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'Анализ' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{ArrowLeft}')
    expect(screen.getByRole('tab', { name: 'Источник' })).toHaveAttribute('aria-selected', 'true')
    await userEvent.keyboard('{Home}')
    expect(screen.getByRole('tab', { name: 'Анализ' })).toHaveAttribute('aria-selected', 'true')
  })
})

describe('ConfirmDialog', () => {
  it('focuses Cancel, traps Tab, confirms, and cancels on Escape', async () => {
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <>
        <button type="button">outside</button>
        <ConfirmDialog title="Проверить?" confirmLabel="Да" onConfirm={onConfirm} onCancel={onCancel}>
          текст
        </ConfirmDialog>
      </>,
    )
    expect(screen.getByRole('alertdialog', { name: 'Проверить?' })).toBeInTheDocument()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Отмена' }))
    await userEvent.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Да' }))
    await userEvent.tab()
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Отмена' }))
    await userEvent.click(screen.getByRole('button', { name: 'Да' }))
    expect(onConfirm).toHaveBeenCalledOnce()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalledOnce()
  })
})
