import { EscalationQueue } from '@/components/dashboard/EscalationQueue'
import { MetricTiles } from '@/components/dashboard/MetricTiles'
import { Page } from '@/components/layout/Page'

/** Manager: the numbers, and the cases waiting for their decision (PLAN.md §3.5). */
export function ManagerConsole() {
  return (
    <Page title="Manager Console">
      <div className="flex flex-col gap-section">
        <MetricTiles />
        <EscalationQueue />
      </div>
    </Page>
  )
}
