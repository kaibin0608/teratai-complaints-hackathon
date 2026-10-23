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

  return (
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
          <StatusMessage icon={Inbox} title="Nothing escalated">
            Cases an officer or analyst escalates (over their limit, or sensitive) appear here.
          </StatusMessage>
        ) : (
          <CaseTable items={result.data.items} />
        ))}
    </Card>
  )
}
