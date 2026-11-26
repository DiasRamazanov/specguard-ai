// Renders docs/release/presentation/specguard-presentation.html to a PDF and per-slide PNG previews.
//   node scripts/export-presentation.mjs
import { chromium } from '@playwright/test'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const dir = path.resolve(here, '..', '..', 'docs', 'release', 'presentation')
const html = path.join(dir, 'specguard-presentation.html')
const previews = path.join(dir, 'previews')
fs.mkdirSync(previews, { recursive: true })

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
const url = pathToFileURL(html).href + '?export'
await page.goto(url)
await page.evaluate(() => document.fonts.ready)
const count = await page.locator('.slide').count()
for (let n = 1; n <= count; n++) {
  await page.goto(url + '#' + n)
  await page.reload()
  await page.evaluate(() => document.fonts.ready)
  await page.waitForTimeout(150)
  await page.screenshot({ path: path.join(previews, `slide-${String(n).padStart(2, '0')}.png`) })
}
await page.emulateMedia({ media: 'print' })
await page.pdf({ path: path.join(dir, 'specguard-presentation.pdf'), width: '1920px', height: '1080px', printBackground: true })
console.log(`exported ${count} slides`)
await browser.close()
