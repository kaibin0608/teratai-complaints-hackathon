interface ImportMetaEnv {
  /** Backend base URL. Empty (default) = same origin; the dev server proxies /api to the backend. */
  readonly VITE_API_URL?: string
  /** Demo clock date, "YYYY-MM-DD". Defaults to 2026-09-30. */
  readonly VITE_DEMO_DATE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
