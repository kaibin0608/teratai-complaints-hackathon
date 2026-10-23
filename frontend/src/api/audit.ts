import type { AuditLog, AuditQuery } from '@/lib/types'
import { request } from './client'

export const auditApi = {
  /** Manager only; newest first. */
  list: (query: AuditQuery = {}, signal?: AbortSignal) => request<AuditLog>('/api/audit', { query: { ...query }, signal }),
}
