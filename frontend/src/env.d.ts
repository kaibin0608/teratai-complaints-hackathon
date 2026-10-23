interface ImportMetaEnv {
  /** Backend base URL. Empty (default) = same origin; the dev server proxies /api to the backend. */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
