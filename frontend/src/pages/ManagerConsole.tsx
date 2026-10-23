import { EscalationQueue } from '@/components/dashboard/EscalationQueue'
import { MetricsDashboard } from '@/components/dashboard/MetricsDashboard'
import { Page } from '@/components/layout/Page'

/** Manager: the cases waiting for their decision first, then the numbers (PLAN.md §3.5). */
export function ManagerConsole() {
  return (
    <Page title="Manager Console">
      <div className="flex flex-col gap-section">
        <EscalationQueue />
        <MetricsDashboard />
      </div>
    </Page>
  )
}
