import { expect, test, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const SAMPLE = path.join(here, 'fixtures', 'sample-tz.md')
const REVISION = path.join(here, 'fixtures', 'revision-tz.md')

const status = (page: Page) => page.getByTestId('spec-status')
const trigger = (page: Page) => page.getByRole('button', { name: /SPEC — дважды/ })
const copilot = (page: Page) => page.locator('aside.copilot')

async function runAudit(page: Page) {
  await page.goto('/')
  await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
  await expect(page.locator('.file-row')).toContainText('загружен')
  await page.getByRole('button', { name: 'Начать анализ' }).click()
  await expect(page.getByRole('heading', { name: 'Результаты аудита' })).toBeVisible()
}

test.describe('audit flow against the offline backend', () => {
  test('upload → real events → results with offline labelling', async ({ page }) => {
    await page.goto('/')
    await expect(status(page)).toHaveAttribute('data-state', 'greeting')
    await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
    await expect(page.locator('.file-row')).toContainText('загружен')
    await page.getByRole('button', { name: 'Начать анализ' }).click()

    // SPEC replays the real event stream: document received → … → success.
    const seen = new Set<string>()
    for (let i = 0; i < 40 && !seen.has('success'); i++) {
      seen.add((await status(page).getAttribute('data-state')) ?? '')
      await page.waitForTimeout(150)
    }
    expect(seen).toContain('upload')
    expect(seen).toContain('success')

    await expect(page.getByRole('heading', { name: 'Результаты аудита' })).toBeVisible()
    await expect(page.getByText('Офлайн · без модели').first()).toBeVisible()
    await expect(page.getByText(/Офлайн-режим\./)).toBeVisible()
    await expect(page.getByRole('button', { name: /Требования/ })).toContainText('8')
  })

  test('contradiction detail and source citation', async ({ page }) => {
    await runAudit(page)
    await page.getByRole('button', { name: /Противоречия/ }).click()
    await page.getByText('Несовместимые нижняя и верхняя границы').click()
    const detail = page.getByTestId('finding-detail')
    await expect(detail.locator('.compare-pair')).toContainText('SG-602')
    await expect(detail.locator('.compare-pair')).toContainText('SG-601')
    await detail.getByRole('tab', { name: 'Источник' }).click()
    await detail.getByRole('tabpanel').locator('button.evidence').first().click()
    const dialog = page.getByRole('dialog', { name: 'Первоисточник' })
    await expect(dialog.locator('mark')).toContainText('Размер пакета')
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  })

  test('report view loads the Markdown report', async ({ page }) => {
    await runAudit(page)
    await page.getByRole('button', { name: /Отчёт/ }).click()
    await expect(page.getByRole('heading', { name: 'Итоговый отчёт' })).toBeVisible()
    await expect(page.locator('.report-md')).not.toBeEmpty()
    await expect(page.getByRole('button', { name: 'Скачать Markdown' })).toBeEnabled()
  })
})

test.describe('SPEC activation and Copilot', () => {
  test('single click acknowledges, double click opens, Escape closes, double click toggles', async ({ page }) => {
    await runAudit(page)
    await expect(copilot(page)).toHaveAttribute('data-open', 'no')
    await trigger(page).click()
    await page.waitForTimeout(400)
    await expect(copilot(page)).toHaveAttribute('data-open', 'no')
    await trigger(page).dblclick()
    await expect(copilot(page)).toHaveAttribute('data-open', 'yes')
    await expect(page.getByRole('button', { name: 'Закрыть Copilot' })).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(copilot(page)).toHaveAttribute('data-open', 'no')
    await expect(trigger(page)).toBeFocused()
    await trigger(page).dblclick()
    await expect(copilot(page)).toHaveAttribute('data-open', 'yes')
    await trigger(page).dblclick({ force: true })
    await expect(copilot(page)).toHaveAttribute('data-open', 'no')
  })

  test('keyboard Enter opens and the close button closes', async ({ page }) => {
    await runAudit(page)
    await trigger(page).focus()
    await page.keyboard.press('Enter')
    await expect(copilot(page)).toHaveAttribute('data-open', 'yes')
    await page.getByRole('button', { name: 'Закрыть Copilot' }).click()
    await expect(copilot(page)).toHaveAttribute('data-open', 'no')
  })

  test('multiple attachments: upload, status, removal; real attachment events', async ({ page }) => {
    await runAudit(page)
    await trigger(page).dblclick()
    await copilot(page).getByLabel('Назначение вложений').selectOption('revision')
    await copilot(page).locator('input[type=file]').setInputFiles([REVISION, SAMPLE])
    const chips = copilot(page).locator('.chip')
    await expect(chips).toHaveCount(2)
    await expect(chips.nth(0)).toContainText('текст извлечён')
    await expect(chips.nth(1)).toContainText('текст извлечён')
    await expect(chips.nth(0)).toContainText('Новая редакция')
    await copilot(page).getByRole('button', { name: 'Удалить sample-tz.md' }).click()
    await expect(chips).toHaveCount(1)
    // Live-only comparison explains itself in offline mode instead of faking a result.
    await copilot(page).getByRole('button', { name: 'Сравнить', exact: true }).click()
    await expect(copilot(page).locator('.reply.error')).toContainText('DeepSeek')
  })

  test('evidence-grounded offline answer with citations', async ({ page }) => {
    await runAudit(page)
    await trigger(page).dblclick()
    await copilot(page).getByLabel('Ваш вопрос').fill('Какой размер пакета записей?')
    await copilot(page).getByRole('button', { name: 'Отправить' }).click()
    const answer = copilot(page).locator('.reply').filter({ hasText: 'офлайн-поиск' })
    await expect(answer).toContainText('Источники')
    await expect(answer.locator('button.evidence').first()).toContainText('SG-60')
    await answer.locator('button.evidence').first().click()
    await expect(page.getByRole('dialog', { name: 'Первоисточник' })).toBeVisible()
  })
})

test.describe('SPEC states and motion', () => {
  test('gaze follows the pointer within the 70% bound and recentres on leave', async ({ page }) => {
    await page.goto('/')
    const gaze = page.locator('.dock .gaze')
    await page.mouse.move(1400, 80)
    await page.waitForTimeout(400)
    const t = (await gaze.getAttribute('transform')) ?? ''
    const [x, y] = t.match(/-?\d+\.\d+/g)!.map(Number)
    expect(x).toBeGreaterThan(3)
    expect(Math.abs(x)).toBeLessThanOrEqual(10.5)
    expect(Math.abs(y)).toBeLessThanOrEqual(6.3)
    await page.locator('.shell').dispatchEvent('pointerleave')
    await page.waitForTimeout(400)
    const [x2, y2] = ((await gaze.getAttribute('transform')) ?? '').match(/-?\d+\.\d+/g)!.map(Number)
    expect(Math.abs(x2)).toBeLessThan(0.2)
    expect(Math.abs(y2)).toBeLessThan(0.2)
  })

  test('backend error → red LED and side-to-side head shake', async ({ page }) => {
    // Error injected at the network layer to exercise the UI deterministically on any OS.
    await page.route('**/api/documents**', (route) =>
      route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Сервис временно недоступен.' }) }),
    )
    await page.goto('/')
    await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
    await expect(status(page)).toHaveAttribute('data-state', 'error')
    const robot = page.locator('.dock .robot')
    await expect(robot).toHaveCSS('--led', '#ef4444')
    const anim = await robot.locator('.spec-body').evaluate((el) => getComputedStyle(el).animationName)
    expect(anim).toContain('spec-error')
    await expect(page.locator('.file-row')).toContainText('Сервис временно недоступен.')
    await expect(page.getByRole('button', { name: 'Повторить загрузку sample-tz.md' })).toBeVisible()
  })

  test('reduced motion disables animation but keeps state colours', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto('/')
    const body = page.locator('.dock .spec-body')
    expect(await body.evaluate((el) => getComputedStyle(el).animationName)).toBe('none')
    await expect(page.locator('.dock .robot')).toHaveCSS('--led', '#facc15')
    await page.mouse.move(1400, 80)
    await page.waitForTimeout(300)
    expect(await page.locator('.dock .gaze').getAttribute('transform')).toBeNull()
  })

  test('motion toggle stops SPEC animation', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Анимация SPEC').uncheck()
    expect(await page.locator('.dock .spec-body').evaluate((el) => getComputedStyle(el).animationName)).toBe('none')
  })
})

test('@mobile explicit Copilot control opens the panel', async ({ page }) => {
  await page.goto('/')
  const open = page.getByRole('button', { name: /^Copilot$/ })
  await expect(open).toBeVisible()
  await open.click()
  await expect(copilot(page)).toHaveAttribute('data-open', 'yes')
  await page.getByRole('button', { name: 'Закрыть Copilot' }).click()
  await expect(copilot(page)).toHaveAttribute('data-open', 'no')
})
