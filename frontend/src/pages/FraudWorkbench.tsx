import { Page } from '@/components/layout/Page'
import { CaseQueue } from '@/components/queue/CaseQueue'
import { FRAUD_TABS } from '@/components/queue/queueTabs'

/** Fraud analyst: fraud queue (PLAN.md §3.4). */
export function FraudWorkbench() {
  return (
    <Page title="Investigation Workbench">
      <CaseQueue tabs={FRAUD_TABS} />
    </Page>
  )
}
