import { expect, test } from '@playwright/test'

// Verifies all 13 approved SPEC states in a real browser using the production component
// (rendered by the dev-only harness at /dev/spec-states.html).
type Fx = 'alert' | 'scan' | 'paper' | 'paper2' | 'spark' | 'dots' | 'glass'
const ALL_FX: Fx[] = ['alert', 'scan', 'paper', 'paper2', 'spark', 'dots', 'glass']

const EXPECTED: Record<string, { led: string; body: string; fx: Fx[] }> = {
  idle: { led: '#facc15', body: 'spec-idle', fx: [] },
  greeting: { led: '#facc15', body: 'spec-happy', fx: [] },
  upload: { led: '#38bdf8', body: 'spec-happy', fx: ['paper'] },
  extract: { led: '#38bdf8', body: 'spec-nod', fx: ['scan'] },
  thinking: { led: '#a78bfa', body: 'spec-think', fx: ['dots'] },
  critical: { led: '#f59e0b', body: 'spec-surprise', fx: ['alert'] },
  verify: { led: '#22d3ee', body: 'spec-think', fx: ['scan', 'glass'] },
  report: { led: '#818cf8', body: 'spec-nod', fx: ['paper'] },
  success: { led: '#22c55e', body: 'spec-happy', fx: ['spark'] },
  error: { led: '#ef4444', body: 'spec-error', fx: ['alert'] },
  attachment: { led: '#facc15', body: 'spec-nod', fx: ['paper'] },
  reading: { led: '#38bdf8', body: 'spec-nod', fx: ['scan'] },
  compare: { led: '#a78bfa', body: 'spec-think', fx: ['paper', 'paper2'] },
}

test.describe('all 13 SPEC states', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dev/spec-states.html')
  })

  test('harness renders exactly the 13 approved states', async ({ page }) => {
    await expect(page.locator('[data-testid^="state-"]')).toHaveCount(13)
  })

  for (const [state, exp] of Object.entries(EXPECTED)) {
    test(`state ${state}: LED, body motion, effects, gold shell`, async ({ page }) => {
      const robot = page.getByTestId(`state-${state}`).locator('svg.robot')
      await expect(robot).toHaveAttribute('data-state', state)
      await expect(robot).toHaveCSS('--led', exp.led)
      const led = await robot.locator('.led').evaluate((el) => getComputedStyle(el).fill)
      expect(led).not.toBe('none')
      const body = await robot.locator('.spec-body').evaluate((el) => getComputedStyle(el).animationName)
      expect(body.split(',')[0].trim()).toBe(exp.body)
      for (const fx of ALL_FX) {
        const opacity = await robot.locator(`.${fx}`).evaluate((el) => getComputedStyle(el).opacity)
        if (exp.fx.includes(fx)) expect(Number(opacity), `${fx} visible in ${state}`).toBeGreaterThan(0.3)
        else expect(Number(opacity), `${fx} hidden in ${state}`).toBe(0)
      }
      await expect(robot.locator('path[fill="#f9c72e"]')).toHaveCount(1)
      await expect(robot.locator('.blink')).toHaveCSS('animation-name', 'spec-blink')
    })
  }

  test('dramatic states settle into the idle float after their short motion', async ({ page }) => {
    for (const s of ['greeting', 'upload', 'success', 'error', 'critical', 'attachment']) {
      const anim = await page.getByTestId(`state-${s}`).locator('.spec-body').evaluate((el) => {
        const cs = getComputedStyle(el)
        return { names: cs.animationName, counts: cs.animationIterationCount }
      })
      expect(anim.names, s).toContain('spec-idle')
      expect(anim.counts.split(',')[0].trim(), s).not.toBe('infinite')
    }
  })

  test('error shakes side to side by ±9°', async ({ page }) => {
    const rules = await page.evaluate(() => {
      for (const sheet of Array.from(document.styleSheets)) {
        for (const rule of Array.from(sheet.cssRules)) {
          if (rule instanceof CSSKeyframesRule && rule.name === 'spec-error') return rule.cssText
        }
      }
      return ''
    })
    expect(rules).toContain('rotate(-9deg)')
    expect(rules).toContain('rotate(9deg)')
  })

  test('measured motion: error shake, success bounce, thinking tilt, compare gaze', async ({ page }) => {
    // Samples real computed transforms over ~1.6 s while the animations run.
    const ranges = await page.evaluate(async () => {
      const m = (sel: string) => new DOMMatrix(getComputedStyle(document.querySelector(sel)!).transform)
      const deg = (x: DOMMatrix) => (Math.atan2(x.b, x.a) * 180) / Math.PI
      const s = { error: [] as number[], errorX: [] as number[], success: [] as number[], thinking: [] as number[], compare: [] as number[] }
      for (let i = 0; i < 32; i++) {
        const e = m('[data-testid=state-error] .spec-body')
        s.error.push(deg(e))
        s.errorX.push(e.e)
        s.success.push(m('[data-testid=state-success] .spec-body').f)
        s.thinking.push(deg(m('[data-testid=state-thinking] .spec-body')))
        s.compare.push(m('[data-testid=state-compare] .gaze-auto').e)
        await new Promise((r) => setTimeout(r, 50))
      }
      const span = (a: number[]) => [Math.min(...a), Math.max(...a)]
      return { error: span(s.error), errorX: span(s.errorX), success: span(s.success), thinking: span(s.thinking), compare: span(s.compare) }
    })
    // Error: pronounced side-to-side head shake, both directions, within ±9°.
    expect(ranges.error[0]).toBeLessThan(-5)
    expect(ranges.error[1]).toBeGreaterThan(5)
    expect(Math.max(Math.abs(ranges.error[0]), Math.abs(ranges.error[1]))).toBeLessThanOrEqual(9.01)
    expect(ranges.errorX[1] - ranges.errorX[0]).toBeGreaterThan(4)
    // Success: happy bounce lifts the body.
    expect(ranges.success[0]).toBeLessThan(-6)
    // Thinking: head tilts both ways.
    expect(ranges.thinking[0]).toBeLessThan(-3)
    expect(ranges.thinking[1]).toBeGreaterThan(3)
    // Compare: eyes alternate between the two documents.
    expect(ranges.compare[0]).toBeLessThan(-5)
    expect(ranges.compare[1]).toBeGreaterThan(5)
  })

  test('compare alternates gaze between the two documents', async ({ page }) => {
    const anim = await page.getByTestId('state-compare').locator('.gaze-auto').evaluate((el) => getComputedStyle(el).animationName)
    expect(anim).toBe('spec-alternate')
  })

  test('70% gaze is bounded and independent of the state animation', async ({ page }) => {
    const card = page.getByTestId('state-error')
    await card.hover()
    await page.mouse.move(1270, 10)
    await page.waitForTimeout(400)
    const t = (await card.locator('.gaze').getAttribute('transform')) ?? ''
    const [x, y] = t.match(/-?\d+\.\d+/g)!.map(Number)
    expect(Math.abs(x)).toBeLessThanOrEqual(10.5)
    expect(Math.abs(y)).toBeLessThanOrEqual(6.3)
    expect(Math.abs(x) + Math.abs(y)).toBeGreaterThan(1)
    expect(await card.locator('.spec-body').evaluate((el) => getComputedStyle(el).animationName)).toContain('spec-error')
  })

  test('visual record of all states', async ({ page }, info) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.reload()
    await info.attach('spec-13-states', { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' })
  })
})
