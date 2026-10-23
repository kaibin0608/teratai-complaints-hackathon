import { metricsApi } from '@/api/metrics'
import { demoNow } from '@/lib/clock'
import type { Metrics } from '@/lib/types'
import { useApi } from './useApi'

const POLL_MS = 10_000

/** Dashboard numbers, with the SLA tiles measured on the demo clock (UI_API.md: use the demo date as `as_of`). */
export function useMetrics() {
  return useApi<Metrics>('metrics', (signal) => metricsApi.get(demoNow().slice(0, 16), signal), { pollMs: POLL_MS })
}
