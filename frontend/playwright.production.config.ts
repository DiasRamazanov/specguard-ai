import { defineConfig } from '@playwright/test'
import local from './playwright.config'

const baseURL = process.env.SPECGUARD_TEST_URL
if (!baseURL) throw new Error('Set SPECGUARD_TEST_URL to the deployment to verify.')

export default defineConfig({
  ...local,
  testMatch: '**/spec.e2e.ts',
  webServer: undefined,
  use: { ...local.use, baseURL },
})
