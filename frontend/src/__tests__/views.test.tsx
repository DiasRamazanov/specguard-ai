import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import fixture from '../../../contracts/fixtures/mock-audit.json'
import type { AuditResult, AuditStatus } from '../api/types'
import { Markdown } from '../components/Markdown'
import { SpecDock } from '../mascot/SpecDock'
import { FindingsView } from '../views/FindingsView'
import { OverviewView } from '../views/OverviewView'
import { pipelineStates } from '../views/ProgressView'

// FIXTURE: contracts/fixtures/mock-audit.json is the backend team's synthetic offline
// result. It is used only in tests and is never presented as live data.
const result = (fixture as { fixture: string; result: unknown }).result as AuditResult
const props = { result, filenames: {}, openSource: vi.fn(), askSpec: vi.fn(), requestRevision: vi.fn(), navigate: vi.fn() }

describe('views against the contract fixture', () => {
  it('fixture is explicitly labelled as mock', () => {
    expect((fixture as { fixture: string }).fixture).toBe('mock')
  })

  it('overview shows the verdict and flags offline mode', () => {
    render(<OverviewView {...props} />)
    expect(screen.getByText('Результаты аудита')).toBeInTheDocument()
    expect(screen.getByText(/Офлайн-режим/)).toBeInTheDocument()
    expect(screen.getByTestId('verdict')).toHaveClass(result.readiness.verdict)
  })

  it('finding detail renders evidence quotes as text', async () => {
    const f = result.findings[0]
    render(<FindingsView {...props} selectedId={f.finding_id} />)
    expect(screen.getAllByText(f.title).length).toBeGreaterThan(0)
    await userEvent.click(screen.getByRole('tab', { name: 'Источник' }))
    const quote = f.evidence.find((e) => e.quote)?.quote
    if (quote) expect(screen.getByText(quote)).toBeInTheDocument()
  })
})

describe('pipeline progress', () => {
  it('derives step state only from reported events', () => {
    const status: AuditStatus = {
      audit_id: 'a',
      status: 'running',
      error: null,
      events: [
        { sequence: 1, stage: 'document_received', time: '', finding_id: null },
        { sequence: 2, stage: 'extracting', time: '', finding_id: null },
      ],
    }
    const s = pipelineStates(status)
    expect(s.document_received).toBe('done')
    expect(s.extracting).toBe('active')
    expect(s.validating_individual).toBe('pending')
    const done = pipelineStates({
      ...status,
      status: 'completed',
      events: [...status.events, { sequence: 3, stage: 'completed', time: '', finding_id: null }],
    })
    expect(done.extracting).toBe('done')
    expect(done.validating_individual).toBe('skipped')
  })
})

describe('Markdown', () => {
  it('never injects HTML from untrusted report content', () => {
    const { container } = render(<Markdown source={'# Отчёт\n- <img src=x onerror=alert(1)>\n**жирный**'} />)
    expect(container.querySelector('img')).toBeNull()
    expect(container.textContent).toContain('<img src=x onerror=alert(1)>')
    expect(container.querySelector('b')?.textContent).toBe('жирный')
  })
})

describe('SpecDock activation', () => {
  function setup(open = false) {
    const onToggle = vi.fn()
    render(<SpecDock state="idle" open={open} onToggle={onToggle} gazeRoot={null} motion onMotionChange={() => {}} />)
    return { onToggle, trigger: screen.getByRole('button', { name: /SPEC — дважды/ }) }
  }

  it('single click only acknowledges', async () => {
    const { onToggle, trigger } = setup()
    await userEvent.click(trigger)
    expect(onToggle).not.toHaveBeenCalled()
  })

  it('double click opens; double click while open closes', async () => {
    const closed = setup(false)
    await userEvent.dblClick(closed.trigger)
    expect(closed.onToggle).toHaveBeenLastCalledWith(true)
  })

  it('double click while open requests close', async () => {
    const opened = setup(true)
    await userEvent.dblClick(opened.trigger)
    expect(opened.onToggle).toHaveBeenLastCalledWith(false)
  })

  it('keyboard Enter and Space toggle', async () => {
    const { onToggle, trigger } = setup()
    trigger.focus()
    await userEvent.keyboard('{Enter}')
    expect(onToggle).toHaveBeenLastCalledWith(true)
    await userEvent.keyboard(' ')
    expect(onToggle).toHaveBeenCalledTimes(2)
  })

  it('exposes an explicit open control for mobile', () => {
    setup()
    expect(screen.getByRole('button', { name: /^Copilot$/ })).toBeInTheDocument()
  })
})
