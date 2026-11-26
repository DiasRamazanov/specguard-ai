import { defineConfig, devices } from '@playwright/test'

// E2E runs the real offline backend (no provider key) plus the Vite dev server with its
// same-origin /api proxy. The backend command runs from the repo root (cwd '..'), so the
// default interpreter path is relative to the repo root. Set SPECGUARD_PYTHON to override.
const python =
  process.env.SPECGUARD_PYTHON ?? (process.platform === 'win32' ? '.venv\\Scripts\\python.exe' : '.venv/bin/python')

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  timeout: 45_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    locale: 'ru-RU',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } }, grepInvert: /@mobile/ },
    { name: 'mobile', use: { ...devices['Pixel 7'] }, grep: /@mobile/ },
  ],
  webServer: [
    {
      command: `${python} -m uvicorn specguard.api:app --host 127.0.0.1 --port 8000 --workers 1`,
      cwd: '..',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: 'npx vite --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
})
