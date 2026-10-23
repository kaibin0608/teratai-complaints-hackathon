import { CircleAlert, Inbox, LoaderCircle, RotateCw } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { Tabs } from '@/components/shared/Tabs'
import { useCaseList } from '@/hooks/useCaseList'
import { cx } from '@/lib/cx'
import { queueLabel } from '@/lib/labels'
import type { CaseList, Queue } from '@/lib/types'
import { CaseTable } from './CaseTable'

type Sort = 'priority' | 'recent'

const PAGE_SIZE = 50
const SORTS: readonly { value: Sort; label: string }[] = [
  { value: 'priority', label: 'Most urgent' },
  { value: 'recent', label: 'Newest' },
]

/**
 * Queue tabs with live counts and a polled case table. The tab and sort live in the URL
 * (`?queue=approved&sort=recent`), so refresh, back and shared links keep them.
 */
export function CaseQueue({ tabs }: { tabs: readonly Queue[] }) {
  const [params, setParams] = useSearchParams()
  const requested = params.get('queue') as Queue | null
  const queue = requested && tabs.includes(requested) ? requested : tabs[0]!
  const sort: Sort = params.get('sort') === 'recent' ? 'recent' : 'priority'

  const update = (next: { queue?: Queue; sort?: Sort }) =>
    setParams((current) => {
      const merged = new URLSearchParams(current)
      if (next.queue) merged.set('queue', next.queue)
      if (next.sort) merged.set('sort', next.sort)
      return merged
    })

  // Remount per tab and sort so paging starts again.
  return <QueueView key={`${queue}:${sort}`} tabs={tabs} queue={queue} sort={sort} onChange={update} />
}

interface QueueViewProps {
  tabs: readonly Queue[]
  queue: Queue
  sort: Sort
  onChange: (next: { queue?: Queue; sort?: Sort }) => void
}

function QueueView({ tabs, queue, sort, onChange }: QueueViewProps) {
  const [limit, setLimit] = useState(PAGE_SIZE)
  const result = useCaseList({ queue, sort, limit })
  const counts: Partial<CaseList['counts']> = result.status === 'success' ? result.data.counts : {}

  return (
    <div className="flex flex-col gap-4">
      <Tabs
        label="Queues"
        value={queue}
        onChange={(value) => onChange({ queue: value })}
        items={tabs.map((value) => ({ value, label: queueLabel[value], count: counts[value] }))}
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div role="group" aria-label="Sort" className="flex rounded-control border border-default p-0.5">
          {SORTS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              aria-pressed={sort === value}
              onClick={() => onChange({ sort: value })}
              className={cx(
                'rounded-control px-2.5 py-1 text-xs font-medium transition-colors',
                sort === value ? 'bg-neutral-100 text-primary' : 'text-secondary hover:text-primary',
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <LiveIndicator result={result} />
      </div>

      <QueueBody result={result} queue={queue} onRetry={result.reload} onMore={() => setLimit((l) => l + PAGE_SIZE)} />
    </div>
  )
}

function LiveIndicator({ result }: { result: ReturnType<typeof useCaseList> }) {
  if (result.status !== 'success') return null
  const { items, total } = result.data
  return (
    <p className="flex items-center gap-2 text-xs text-secondary">
      <span aria-hidden className="size-1.5 rounded-full bg-success-500" />
      Live · {items.length} of {total}
    </p>
  )
}

interface QueueBodyProps {
  result: ReturnType<typeof useCaseList>
  queue: Queue
  onRetry: () => void
  onMore: () => void
}

function QueueBody({ result, queue, onRetry, onMore }: QueueBodyProps) {
  if (result.status === 'loading') return <StatusMessage busy icon={LoaderCircle} title="Loading cases…" />
  if (result.status === 'error') {
    return (
      <StatusMessage
        icon={CircleAlert}
        title="Could not load the queue"
        action={
          <Button onClick={onRetry}>
            <RotateCw size={16} aria-hidden />
            Retry
          </Button>
        }
      >
        {result.error.message}
      </StatusMessage>
    )
  }
  const { items, total } = result.data
  if (items.length === 0) {
    return (
      <StatusMessage icon={Inbox} title={`No cases in ${queueLabel[queue]}`}>
        New complaints appear here on their own.
      </StatusMessage>
    )
  }
  return (
    <>
      <CaseTable items={items} />
      {items.length < total && (
        <div className="flex justify-center">
          <Button onClick={onMore}>Load more ({total - items.length} left)</Button>
        </div>
      )}
    </>
  )
}
