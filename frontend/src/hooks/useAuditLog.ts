import { auditApi } from '@/api/audit'
import type { AuditLog, AuditQuery } from '@/lib/types'
import { useApi } from './useApi'

const POLL_MS = 5000

export function useAuditLog(query: AuditQuery) {
  return useApi<AuditLog>(`audit:${JSON.stringify(query)}`, (signal) => auditApi.list(query, signal), { pollMs: POLL_MS })
}
