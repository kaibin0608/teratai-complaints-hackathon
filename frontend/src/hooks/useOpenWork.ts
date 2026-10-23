import { casesApi } from '@/api/cases'
import type { CaseList } from '@/lib/types'
import { useApi } from './useApi'

const POLL_MS = 10_000
const PAGE = 500 // the backend's largest page

/**
 * Every case still waiting for people (approval and fraud queues), for the manager's alerts and team workload.
 * Pages through the list: one page of 500 silently undercounted once more than 500 cases were open.
 */
export function useOpenWork() {
  return useApi<CaseList>(
    'open-work',
    async (signal) => {
      const query = { queue: ['awaiting_approval', 'with_fraud_team'], sort: 'priority', limit: PAGE } as const
      const first = await casesApi.list({ ...query, queue: [...query.queue] }, signal)
      const items = [...first.items]
      while (items.length < first.total) {
        const next = await casesApi.list({ ...query, queue: [...query.queue], offset: items.length }, signal)
        if (next.items.length === 0) break
        items.push(...next.items)
      }
      return { ...first, items }
    },
    { pollMs: POLL_MS, keepPrevious: true },
  )
}
