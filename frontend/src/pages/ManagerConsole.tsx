import { EscalationQueue } from '@/components/dashboard/EscalationQueue'
import { MetricsDashboard } from '@/components/dashboard/MetricsDashboard'
import { NoticeBanner } from '@/components/layout/NoticeBanner'
import { Page } from '@/components/layout/Page'

/** Manager: the cases waiting for their decision first, then the numbers (PLAN.md §3.5). */
export function ManagerConsole() {
  return (
    <Page title="Manager Console">
      <div className="flex flex-col gap-section">
        <NoticeBanner />
        <EscalationQueue />
        <MetricsDashboard />
      </div>
    </Page>
  )
}
