import type { Metrics } from '@/lib/types'
import { request } from './client'

export const metricsApi = {
  /** Manager only. The SLA tiles are measured as of now. */
  get: (signal?: AbortSignal) => request<Metrics>('/api/metrics', { signal }),
}
