import { slaAsOf } from '@/lib/clock'
import type { Metrics } from '@/lib/types'
import { request } from './client'

export const metricsApi = {
  /** Manager only. The SLA tiles are measured on the SLA clock (lib/clock.ts), the same as the queues. */
  get: (signal?: AbortSignal) => {
    const asOf = slaAsOf()
    return request<Metrics>('/api/metrics', { signal, query: asOf ? { as_of: asOf } : undefined })
  },
}
