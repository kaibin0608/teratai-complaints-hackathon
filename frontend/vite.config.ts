import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/**
 * FastAPI backend the dev server forwards /api to (docs/UI_API.md). 127.0.0.1 rather than localhost:
 * on Windows, localhost tries IPv6 first and adds ~0.2 s to every call.
 */
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://127.0.0.1:8000'

// /complaints is the organisers' intake route (docs/api.md). /cases is NOT proxied: it is also a page here.
const proxy = { '/api': BACKEND_URL, '/complaints': BACKEND_URL }

const REPO_ROOT = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // The bank's policy files: the Policy page reads the same CSVs the backend applies.
      '@data': fileURLToPath(new URL('../data', import.meta.url)),
    },
  },
  // `npm run dev` and `npm run preview` (the built app) reach the backend the same way.
  // fs.allow lets the dev server read ../data (it sits outside this folder).
  server: { proxy, fs: { allow: [REPO_ROOT] } },
  preview: { proxy },
})
