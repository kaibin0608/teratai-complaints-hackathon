import { Page } from '@/components/layout/Page'
import { CaseQueue } from '@/components/queue/CaseQueue'
import { OFFICER_TABS } from '@/components/queue/queueTabs'

/** Complaints officer: approval queue (PLAN.md §3.3). */
export function OfficerDesk() {
  return (
    <Page title="Resolution Desk">
      <CaseQueue tabs={OFFICER_TABS} />
    </Page>
  )
}
