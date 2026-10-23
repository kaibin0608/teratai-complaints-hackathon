import { casesApi } from '@/api/cases'
import type { CaseList, CaseListQuery } from '@/lib/types'
import { useApi } from './useApi'

/** UI_API.md: poll the list every 3–5 s so new complaints appear on their own. */
const POLL_MS = 4000

export function useCaseList(query: CaseListQuery) {
  return useApi<CaseList>(`cases:${JSON.stringify(query)}`, (signal) => casesApi.list(query, signal), {
    pollMs: POLL_MS,
    keepPrevious: true,
  })
}
