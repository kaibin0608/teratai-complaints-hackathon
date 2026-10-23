import { EscalationQueue } from '@/components/dashboard/EscalationQueue'
import { MetricsDashboard } from '@/components/dashboard/MetricsDashboard'
import { NeedsYou } from '@/components/dashboard/NeedsYou'
import { OverrideFeed } from '@/components/dashboard/OverrideFeed'
import { TeamWorkload } from '@/components/dashboard/TeamWorkload'
import { Page } from '@/components/layout/Page'

/**
 * Manager: what needs a decision first (alerts, then the escalated cases), then the day in four numbers, who holds
 * the work and where people changed the agent, and last the charts that explain why (PLAN.md §3.5).
 */
export function ManagerConsole() {
  return (
    <Page title="Manager Console">
      <div className="flex flex-col gap-section">
        <NeedsYou />
        <EscalationQueue />
        <MetricsDashboard
          between={
            <div className="grid items-start gap-section lg:grid-cols-2">
              <TeamWorkload />
              <OverrideFeed />
            </div>
          }
        />
      </div>
    </Page>
  )
}
