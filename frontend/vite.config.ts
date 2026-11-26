/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Same-origin dev proxy (docs/architecture.md §6): the backend stays on loopback.
const backend = process.env.SPECGUARD_API ?? 'http://127.0.0.1:8000'
const proxy = {
  '/api': { target: backend, changeOrigin: false, rewrite: (p: string) => p.replace(/^\/api/, '') },
}

export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true, proxy },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true, proxy },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
})
