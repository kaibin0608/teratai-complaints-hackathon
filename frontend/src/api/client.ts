/**
 * Single HTTP entry point to the backend. Every resource module in src/api/ goes through request().
 *
 * - Base URL: VITE_API_URL, or same origin (the Vite dev server proxies /api to the backend).
 * - Auth: the bearer token set by the auth context is attached to every request.
 * - Errors: non-2xx and network failures throw ApiError; a 401 also notifies the auth context.
 */
import type { ErrorBody, Money } from '@/lib/types'

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

let authToken: string | null = null
let onUnauthorized: (() => void) | null = null

export function setAuthToken(token: string | null): void {
  authToken = token
}

/** Called once by the auth context; fires when the backend rejects the token. */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

export class ApiError extends Error {
  /** HTTP status; 0 when the server could not be reached. */
  readonly status: number
  /** Self-check problems of a refused reply (422). */
  readonly problems: string[]
  /** Over-limit refusal (403): why, the user's limit and the amount. */
  readonly limit: { why: string; limit: Money; amount: Money } | null

  constructor(status: number, message: string, details: Partial<Pick<ApiError, 'problems' | 'limit'>> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.problems = details.problems ?? []
    this.limit = details.limit ?? null
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
type QueryValue = string | number | boolean | undefined | readonly (string | number)[]

interface RequestOptions {
  method?: Method
  body?: unknown
  /** Arrays are sent comma-separated (`queue=approved,rejected`); undefined values are dropped. */
  query?: Record<string, QueryValue>
  signal?: AbortSignal
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, signal } = options
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}${toQueryString(query)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'Cannot reach the server. Check that the backend is running.')
  }

  if (response.status === 401) onUnauthorized?.()
  if (!response.ok) throw await toApiError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

function toQueryString(query: RequestOptions['query']): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue
    params.set(key, Array.isArray(value) ? value.join(',') : String(value))
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

async function toApiError(response: Response): Promise<ApiError> {
  const fallback = `Request failed (${response.status} ${response.statusText})`
  let detail: ErrorBody['detail'] | undefined
  try {
    detail = ((await response.json()) as Partial<ErrorBody>).detail
  } catch {
    return new ApiError(response.status, fallback)
  }
  if (typeof detail === 'string') return new ApiError(response.status, detail)
  if (Array.isArray(detail)) {
    return new ApiError(response.status, detail.map((issue) => `${issue.loc.slice(1).join('.')}: ${issue.msg}`).join('; '))
  }
  if (detail && typeof detail === 'object') {
    const limit =
      detail.why && detail.limit && detail.amount ? { why: detail.why, limit: detail.limit, amount: detail.amount } : undefined
    return new ApiError(response.status, detail.why ? `${detail.error}: ${detail.why}` : detail.error, {
      problems: detail.problems,
      limit,
    })
  }
  return new ApiError(response.status, fallback)
}
