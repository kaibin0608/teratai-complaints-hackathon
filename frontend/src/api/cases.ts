import type { ActionBodies, CaseAction, CaseDetail, CaseList, CaseListQuery } from '@/lib/types'
import { request } from './client'

const casePath = (complaintId: string) => `/api/cases/${encodeURIComponent(complaintId)}`

export const casesApi = {
  /** Role-filtered by the backend; `counts` always cover every case the user can see. */
  list: (query: CaseListQuery = {}, signal?: AbortSignal) =>
    request<CaseList>('/api/cases', { query: { ...query }, signal }),

  get: (complaintId: string, signal?: AbortSignal) => request<CaseDetail>(casePath(complaintId), { signal }),

  /** Platform action (needs a token). Returns the full case detail to redraw from. */
  act: <A extends CaseAction>(complaintId: string, action: A, body: ActionBodies[A]) =>
    request<CaseDetail>(`${casePath(complaintId)}/${action}`, { method: 'POST', body }),
}
