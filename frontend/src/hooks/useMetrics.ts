import { metricsApi } from '@/api/metrics'
import type { Metrics } from '@/lib/types'
import { useApi } from './useApi'

const POLL_MS = 10_000

/** Dashboard numbers. */
export function useMetrics() {
  return useApi<Metrics>('metrics', (signal) => metricsApi.get(signal), { pollMs: POLL_MS })
}
