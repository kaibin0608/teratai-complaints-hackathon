import { CircleAlert, Inbox, LoaderCircle, RotateCw, SearchX } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { Tabs } from '@/components/shared/Tabs'
import { useAuth } from '@/hooks/useAuth'
import { useCaseList } from '@/hooks/useCaseList'
import { cx } from '@/lib/cx'
import { queueLabel } from '@/lib/labels'
import type { CaseList, Queue } from '@/lib/types'
import { CaseTable } from './CaseTable'
import { QueueFilters } from './QueueFilters'
import { activeFilters, readParams, toQuery, withParam, type QueueParams, type Sort } from './queueParams'

const PAGE_SIZE = 50
const SORTS: readonly { value: Sort; label: string }[] = [
  { value: 'priority', label: 'Most urgent' },
  { value: 'recent', label: 'Newest' },
]

/**
 * Queue tabs with live counts, search and filters, and a polled case table. Everything the user chose lives in the
 * URL (`?queue=approved&category=FEE_DISPUTE&q=aisyah`), so refresh, back and shared links keep it.
 */
export function CaseQueue({ tabs }: { tabs: readonly Queue[] }) {
  const auth = useAuth()
  const [urlParams, setUrlParams] = useSearchParams()
  const params = readParams(urlParams, tabs)
  const [paging, setPaging] = useState({ signature: '', limit: PAGE_SIZE })

  // Paging starts again whenever the tab, sort or a filter changes.
  const signature = JSON.stringify({ ...params, q: params.q.trim() })
  const limit = paging.signature === signature ? paging.limit : PAGE_SIZE
  const result = useCaseList(toQuery(params, limit))

  const change = (key: keyof QueueParams, value: string | boolean | null) =>
    setUrlParams((current) => withParam(current, key, value), { replace: key !== 'queue' && key !== 'sort' })
  const clear = () => setUrlParams((current) => new URLSearchParams([...current].filter(([key]) => key === 'queue' || key === 'sort')), { replace: true })

  const counts: Partial<CaseList['counts']> = result.status === 'success' ? result.data.counts : {}
  const workflowCounts = result.status === 'success' ? result.data.workflow_counts : undefined

  return (
    <div className="flex flex-col gap-4">
      <Tabs
        label="Queues"
        value={params.queue}
        onChange={(value) => change('queue', value)}
        items={tabs.map((value) => ({ value, label: queueLabel[value], count: counts[value] }))}
      />

      <QueueFilters
        params={params}
        workflowCounts={workflowCounts}
        showChanged={auth.status === 'signed_in' && auth.user.role === 'manager'}
        onChange={change}
        onClear={clear}
        trailing={
          <>
            <div role="group" aria-label="Sort" className="flex rounded-control border border-default p-0.5">
              {SORTS.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={params.sort === value}
                  onClick={() => change('sort', value)}
                  className={cx(
                    'rounded-control px-2.5 py-1 text-xs font-medium transition-colors',
                    params.sort === value ? 'bg-neutral-100 text-primary' : 'text-secondary hover:text-primary',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <LiveIndicator result={result} />
          </>
        }
      />

      <QueueBody
        result={result}
        params={params}
        onRetry={result.reload}
        onMore={() => setPaging({ signature, limit: limit + PAGE_SIZE })}
      />
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
  params: QueueParams
  onRetry: () => void
  onMore: () => void
}

function QueueBody({ result, params, onRetry, onMore }: QueueBodyProps) {
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
    return activeFilters(params) > 0 ? (
      <StatusMessage icon={SearchX} title="No cases match these filters">
        Try removing a filter, or clear them all.
      </StatusMessage>
    ) : (
      <StatusMessage icon={Inbox} title={`No cases in ${queueLabel[params.queue]}`}>
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
