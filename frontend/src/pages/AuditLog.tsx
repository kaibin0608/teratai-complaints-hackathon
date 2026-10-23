import { AuditLogView } from '@/components/audit/AuditLogView'
import { Page } from '@/components/layout/Page'

/** Manager: who did what, when and why (PLAN.md §3.5; append-only). */
export function AuditLog() {
  return (
    <Page title="Audit log">
      <AuditLogView />
    </Page>
  )
}
