import { casesApi } from '@/api/cases'
import type { CaseDetail } from '@/lib/types'
import { useApi } from './useApi'

/** UI_API.md: poll a case every 2 s only while the agent is working on it. */
const POLL_MS = 2000

export const isAgentWorking = ({ case: c }: CaseDetail) => c.status === 'processing' || c.workflow === 'reprocessing'

export function useCaseDetail(complaintId: string) {
  return useApi<CaseDetail>(`case:${complaintId}`, (signal) => casesApi.get(complaintId, signal), {
    pollMs: POLL_MS,
    pollWhile: isAgentWorking,
  })
}
