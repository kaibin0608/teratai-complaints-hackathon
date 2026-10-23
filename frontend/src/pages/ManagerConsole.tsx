import { EscalationQueue } from '@/components/dashboard/EscalationQueue'
import { MetricsDashboard } from '@/components/dashboard/MetricsDashboard'
import { NeedsYou } from '@/components/dashboard/NeedsYou'
import { Page } from '@/components/layout/Page'

/**
 * Manager: what needs a decision first (alerts, then the escalated cases), then the day in four numbers, and below
 * them who holds the work, where people changed the agent, the money and how the process is doing (PLAN.md §3.5).
 * No chart wall: a number belongs here only if a manager would act on it.
 */
export function ManagerConsole() {
  return (
    <Page title="Manager Console">
      <div className="flex flex-col gap-section">
        <NeedsYou />
        <EscalationQueue />
        <MetricsDashboard />
      </div>
    </Page>
  )
}
