interface ImportMetaEnv {
  /** Backend base URL. Empty (default) = same origin; the dev server proxies /api to the backend. */
  readonly VITE_API_URL?: string
  /** "Now" for SLA deadlines, e.g. 2026-09-30T16:30:00 (the complaints' calendar). Empty = the real time. */
  readonly VITE_SLA_NOW?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
