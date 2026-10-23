import { CircleAlert, LoaderCircle, RotateCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { Tabs } from '@/components/shared/Tabs'
import { useMetrics } from '@/hooks/useMetrics'
import { Headline } from './Headline'
import { AgentTab, OverviewTab, PeopleTab } from './MetricsTabs'

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'agent', label: 'The agent' },
  { value: 'people', label: 'People and refunds' },
] as const

/** Loads `GET /api/metrics` once (polled): the headline numbers, then three tabs of detail. */
export function MetricsDashboard() {
  const result = useMetrics()
  const [tab, setTab] = useState<(typeof TABS)[number]['value']>('overview')
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
      <Tabs label="Dashboard sections" items={TABS} value={tab} onChange={setTab} />
      {tab === 'overview' && <OverviewTab m={m} />}
      {tab === 'agent' && <AgentTab m={m} />}
      {tab === 'people' && <PeopleTab m={m} />}
    </div>
  )
}
