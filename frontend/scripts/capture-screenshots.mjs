// Captures real application screenshots for the presentation.
// Requires the offline backend on :8000 and `vite` on :5173. Usage:
//   node scripts/capture-screenshots.mjs <output-dir>
// All screens show offline mode on the synthetic e2e fixture (no model inference).
import { chromium, devices } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'

const here = path.dirname(fileURLToPath(import.meta.url))
const out = path.resolve(process.argv[2] ?? path.join(here, '..', 'screenshots'))
fs.mkdirSync(out, { recursive: true })
const SAMPLE = path.join(here, '..', 'e2e', 'fixtures', 'sample-tz.md')
const REVISION = path.join(here, '..', 'e2e', 'fixtures', 'revision-tz.md')
const BASE = 'http://127.0.0.1:5173'

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: 'ru-RU' })
const page = await ctx.newPage()
const shot = async (name, opts = {}) => {
  await page.waitForTimeout(400)
  await page.screenshot({ path: path.join(out, `${name}.png`), ...opts })
  console.log('saved', name)
}

// 1. Landing
await page.goto(BASE)
await page.mouse.move(1100, 300)
await page.waitForTimeout(2600) // greeting bounce settles
await shot('01-landing')

// 2. Upload ready
await page.getByLabel('Выбрать файлы технического задания').setInputFiles(SAMPLE)
await page.locator('.file-row').filter({ hasText: 'загружен' }).waitFor()
await page.locator('.upload-card').scrollIntoViewIfNeeded()
await shot('02-upload')

// 3. Results overview
await page.getByRole('button', { name: 'Начать анализ' }).click()
await page.getByRole('heading', { name: 'Результаты аудита' }).waitFor()
await page.waitForTimeout(4200) // let SPEC replay real events and settle on success
await shot('03-overview')

// 4. Requirements with detail
await page.getByRole('button', { name: /Требования/ }).click()
await page.locator('.list-row').nth(3).click()
await shot('04-requirements')

// 5. Contradiction detail
await page.getByRole('button', { name: /Противоречия/ }).click()
await page.getByText('Несовместимые нижняя и верхняя границы').click()
await shot('05-contradiction')

// 6. Source evidence drawer
const detail = page.getByTestId('finding-detail')
await detail.getByRole('tab', { name: 'Источник' }).click()
await detail.getByRole('tabpanel').locator('button.evidence').first().click()
await page.getByRole('dialog', { name: 'Первоисточник' }).waitFor()
await shot('06-source-evidence')
await page.keyboard.press('Escape')

// 7. Copilot: attachments + grounded answer
await detail.getByRole('tab', { name: 'Анализ' }).click()
await page.getByRole('button', { name: /SPEC — дважды/ }).dblclick()
const cp = page.locator('aside.copilot')
await cp.getByLabel('Назначение вложений').selectOption('revision')
await cp.locator('input[type=file]').setInputFiles([REVISION])
await cp.locator('.chip').filter({ hasText: 'текст извлечён' }).waitFor()
await cp.getByLabel('Ваш вопрос').fill('Какой размер пакета записей?')
await cp.getByRole('button', { name: 'Отправить' }).click()
await cp.locator('.reply').filter({ hasText: 'офлайн-поиск' }).waitFor()
await page.waitForTimeout(800)
await shot('07-copilot')
await page.keyboard.press('Escape')

// 8. Report
await page.getByRole('button', { name: /Отчёт/ }).click()
await page.locator('.report-md h1, .report-md h2').first().waitFor()
await shot('08-report')

// 10. All 13 SPEC states (dev-only harness, reduced motion for a stable frame)
await page.emulateMedia({ reducedMotion: 'reduce' })
await page.goto(`${BASE}/dev/spec-states.html`)
await page.waitForTimeout(600)
await shot('10-spec-states', { fullPage: true })
await page.emulateMedia({ reducedMotion: 'no-preference' })

// 11. Mobile
const mctx = await browser.newContext({ ...devices['Pixel 7'], locale: 'ru-RU' })
const m = await mctx.newPage()
await m.goto(BASE)
await m.waitForTimeout(1500)
await m.screenshot({ path: path.join(out, '11-mobile.png') })
console.log('saved 11-mobile')

await browser.close()
