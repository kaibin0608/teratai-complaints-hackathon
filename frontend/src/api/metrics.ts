import type { IsoTime, Metrics } from '@/lib/types'
import { request } from './client'

export const metricsApi = {
  /** Manager only. `asOf` is the clock for the SLA tiles: the complaints are from the past, so pass the demo clock. */
  get: (asOf: IsoTime, signal?: AbortSignal) => request<Metrics>('/api/metrics', { query: { as_of: asOf }, signal }),
}
