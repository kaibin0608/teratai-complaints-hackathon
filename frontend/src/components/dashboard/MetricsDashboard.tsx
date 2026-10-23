import { CircleAlert, LoaderCircle, RotateCw } from 'lucide-react'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useMetrics } from '@/hooks/useMetrics'
import { Breakdowns } from './Breakdowns'
import { MetricTiles } from './MetricTiles'

/** Loads `GET /api/metrics` once (polled) and lays out the tiles and charts from it. */
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
  return (
    <div className="flex flex-col gap-section">
      <MetricTiles m={result.data} />
      <Breakdowns m={result.data} />
    </div>
  )
}
