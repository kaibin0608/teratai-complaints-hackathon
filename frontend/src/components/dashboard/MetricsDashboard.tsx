import { CircleAlert, LoaderCircle, RotateCw } from 'lucide-react'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useMetrics } from '@/hooks/useMetrics'
import { Headline } from './Headline'
import { OverrideFeed } from './OverrideFeed'
import { MoneyCard, ProcessCard } from './ProcessAndMoney'
import { TeamWorkload } from './TeamWorkload'

/**
 * The day at a glance: four numbers, then two columns. Left is the work (who holds it, what it is worth); right is the
 * agent (where people changed it, how the process is doing). Loads `GET /api/metrics`, polled.
 */
export function MetricsDashboard() {
  const result = useMetrics()
  if (result.status === 'loading') return <StatusMessage busy icon={LoaderCircle} title="Loading the numbers…" />
  if (result.status === 'error') {
    return (
      <StatusMessage
        icon={CircleAlert}
        title="Could not load the dashboard numbers"
        action={
          <Button onClick={result.reload}>
            <RotateCw size={16} aria-hidden />
            Retry
          </Button>
        }
      >
        {result.error.message}
      </StatusMessage>
    )
  }
  const m = result.data
  return (
    <div className="flex flex-col gap-section">
      <Headline m={m} />
      <div className="grid items-start gap-section lg:grid-cols-2">
        <div className="flex flex-col gap-section">
          <TeamWorkload />
          <MoneyCard m={m} />
        </div>
        <div className="flex flex-col gap-section">
          <OverrideFeed />
          <ProcessCard m={m} />
        </div>
      </div>
    </div>
  )
}
