import { casesApi } from '@/api/cases'
import type { CaseDetail } from '@/lib/types'
import { useApi } from './useApi'

export function useCaseDetail(complaintId: string) {
  return useApi<CaseDetail>(`case:${complaintId}`, (signal) => casesApi.get(complaintId, signal))
}
