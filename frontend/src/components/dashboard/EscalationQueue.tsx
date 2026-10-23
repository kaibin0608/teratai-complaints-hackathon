import { CircleAlert, Inbox, LoaderCircle, RotateCw } from 'lucide-react'
import { CaseTable } from '@/components/queue/CaseTable'
import { Button } from '@/components/shared/Button'
import { Card } from '@/components/shared/Card'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useCaseList } from '@/hooks/useCaseList'

/** Cases an officer or analyst passed up (both teams): they wait for the manager. Open one to decide. */
export function EscalationQueue() {
  const result = useCaseList({ workflow: 'escalated', sort: 'priority', limit: 50 })
  const total = result.status === 'success' ? result.data.total : undefined
  // Nothing escalated: no card at all. The "Needs you" list above already says all is clear.
  if (total === 0) return null

  return (
    <div id="escalated" className="scroll-mt-4">
    <Card title="Escalated: waiting for you" aside={total !== undefined && <span className="text-xs text-secondary tabular-nums">{total}</span>}>
      {result.status === 'loading' && <StatusMessage busy icon={LoaderCircle} title="Loading…" />}
      {result.status === 'error' && (
        <StatusMessage
          icon={CircleAlert}
          title="Could not load the escalations"
          action={
            <Button onClick={result.reload}>
              <RotateCw size={16} aria-hidden />
              Retry
            </Button>
          }
        >
          {result.error.message}
        </StatusMessage>
      )}
      {result.status === 'success' &&
        (result.data.items.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-secondary">
            <Inbox size={16} aria-hidden />
            Nothing is waiting for you. Cases an officer or analyst escalates (over their limit, or sensitive) appear here.
          </p>
        ) : (
          <CaseTable items={result.data.items} />
        ))}
    </Card>
    </div>
  )
}
