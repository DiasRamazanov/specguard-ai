import { expect, test, type Page } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const SAMPLE = path.join(here, 'fixtures', 'sample-tz.md')

async function runAudit(page: Page) {
  await page.goto('/')
  await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
  await expect(page.locator('.file-row')).toContainText('загружен')
  await page.getByRole('button', { name: 'Начать анализ' }).click()
  await expect(page.getByRole('heading', { name: 'Результаты аудита' })).toBeVisible()
}

test.describe('frontend-enhance: navigation and accessibility', () => {
  test('views are deep-linked and the browser Back button moves between them', async ({ page }) => {
    await runAudit(page)
    await expect(page).toHaveURL(/#\/overview$/)
    await expect(page).toHaveTitle('Обзор · SpecGuard AI')
    await page.getByRole('button', { name: /Противоречия/ }).click()
    await expect(page).toHaveURL(/#\/contradictions$/)
    await expect(page).toHaveTitle('Противоречия · SpecGuard AI')
    await page.getByText('Несовместимые нижняя и верхняя границы').click()
    await expect(page).toHaveURL(/#\/contradictions\/finding-/)
    await page.goBack()
    await expect(page).toHaveURL(/#\/contradictions$/)
    await page.goBack()
    await expect(page.getByRole('heading', { name: 'Результаты аудита' })).toBeVisible()
    await page.goForward()
    await expect(page.getByRole('heading', { name: /Противоречия/ })).toBeVisible()
  })

  test('sidebar navigation moves focus to the new heading', async ({ page }) => {
    await runAudit(page)
    await page.getByRole('button', { name: /Требования/ }).click()
    await expect(page.getByRole('heading', { level: 1, name: /Требования/ })).toBeFocused()
  })

  test('skip link is first in tab order and jumps to the content', async ({ page }) => {
    await page.goto('/')
    await page.keyboard.press('Tab')
    const skip = page.getByRole('link', { name: 'Перейти к содержимому' })
    await expect(skip).toBeFocused()
    await expect(skip).toBeInViewport()
    await page.keyboard.press('Enter')
    await expect(page.locator('#main')).toBeFocused()
  })

  test('source dialog traps focus and returns it to the citation', async ({ page }) => {
    await runAudit(page)
    await page.getByRole('button', { name: /Противоречия/ }).click()
    await page.getByText('Несовместимые нижняя и верхняя границы').click()
    const detail = page.getByTestId('finding-detail')
    await detail.getByRole('tab', { name: 'Источник' }).click()
    const citation = detail.getByRole('tabpanel').locator('button.evidence').first()
    await citation.click()
    const dialog = page.getByRole('dialog', { name: 'Первоисточник' })
    await expect(dialog.getByRole('button', { name: 'Закрыть источник' })).toBeFocused()
    await page.keyboard.press('Tab')
    await page.keyboard.press('Tab')
    await expect(dialog.getByRole('button', { name: 'Закрыть источник' })).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(citation).toBeFocused()
  })

  test('disabled start explains why', async ({ page }) => {
    await page.goto('/')
    const start = page.getByRole('button', { name: 'Начать анализ' })
    await expect(start).toBeDisabled()
    await expect(page.locator('#start-help')).toHaveText('Добавьте хотя бы один документ PDF, Markdown или TXT.')
    await expect(start).toHaveAttribute('aria-describedby', 'start-help')
  })

  test('error toasts can be dismissed', async ({ page }) => {
    await page.route('**/api/documents**', (route) =>
      route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Сервис временно недоступен.' }) }),
    )
    await page.goto('/')
    await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
    const toast = page.locator('.toast').filter({ hasText: 'Сервис временно недоступен.' })
    await expect(toast).toBeVisible()
    await toast.getByRole('button', { name: 'Закрыть уведомление' }).click()
    await expect(toast).toBeHidden()
  })
})

test('@mobile touch targets are at least 44px and nothing overflows horizontally', async ({ page }) => {
  await runAudit(page)
  await page.getByRole('button', { name: /Противоречия/ }).click()
  await page.getByText('Несовместимые нижняя и верхняя границы').click()
  const report = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth
    const small = [...document.querySelectorAll('main button, main [role=tab], nav button')]
      .map((el) => el.getBoundingClientRect())
      .filter((r) => r.width > 0 && r.height < 43.5).length
    return { overflow: document.documentElement.scrollWidth > vw + 1, small }
  })
  expect(report.overflow).toBe(false)
  expect(report.small).toBe(0)
})
