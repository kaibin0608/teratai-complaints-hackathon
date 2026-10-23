import { casesApi } from '@/api/cases'
import type { CaseList } from '@/lib/types'
import { useApi } from './useApi'

const POLL_MS = 10_000

/** Every case still waiting for people (approval and fraud queues), for the manager's alerts and team workload. */
export function useOpenWork() {
  return useApi<CaseList>(
    'open-work',
    (signal) => casesApi.list({ queue: ['awaiting_approval', 'with_fraud_team'], sort: 'priority', limit: 500 }, signal),
    { pollMs: POLL_MS, keepPrevious: true },
  )
}
