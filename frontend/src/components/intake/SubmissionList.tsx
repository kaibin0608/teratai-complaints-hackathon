import { CircleAlert, CircleCheck, LoaderCircle } from 'lucide-react'
import { Link } from 'react-router'
import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { useAuth } from '@/hooks/useAuth'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import type { Submission } from '@/hooks/useSubmissions'
import { routeLabel } from '@/lib/labels'
import { paths } from '@/lib/paths'

/** What happened to each complaint sent from this page, newest first. */
export function SubmissionList({ submissions }: { submissions: readonly Submission[] }) {
  if (submissions.length === 0) return null
  return (
    <Card title="Sent from this page" aside={<span className="text-xs text-secondary">{submissions.length}</span>}>
      <ul className="divide-y divide-neutral-100">
        {submissions.map((submission) => (
          <li key={submission.complaint.complaint_id} className="flex flex-wrap items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
            <div className="min-w-0">
              <p className="text-sm font-medium text-primary">{submission.complaint.complaint_id}</p>
              <p className="max-w-md truncate text-xs text-secondary">{submission.complaint.text}</p>
            </div>
            <Outcome submission={submission} />
          </li>
        ))}
      </ul>
    </Card>
  )
}

function Outcome({ submission }: { submission: Submission }) {
  if (submission.state === 'sending') {
    return (
      <Badge tone="info" icon={LoaderCircle}>
        Sending…
      </Badge>
    )
  }
  if (submission.state === 'failed') {
    return (
      <span className="flex items-center gap-1.5 text-sm text-error-700">
        <CircleAlert size={14} aria-hidden />
        {submission.error}
      </span>
    )
  }
  return <ReceivedOutcome id={submission.complaint.complaint_id} />
}

/**
 * The manager sees every case, so the page follows it live: processing, then its queue, then a link.
 * Officers and analysts only see their own queues, so they just get the confirmation.
 */
function ReceivedOutcome({ id }: { id: string }) {
  const auth = useAuth()
  if (auth.status !== 'signed_in' || auth.user.role !== 'manager') {
    return (
      <Badge tone="success" icon={CircleCheck}>
        Received: it will appear in its queue
      </Badge>
    )
  }
  return <ManagerTracker id={id} />
}

function ManagerTracker({ id }: { id: string }) {
  const result = useCaseDetail(id)
  if (result.status !== 'success') {
    return (
      <Badge tone="info" icon={LoaderCircle}>
        Received
      </Badge>
    )
  }
  const { case: c, decision } = result.data
  if (c.status === 'processing') {
    return (
      <Badge tone="info" icon={LoaderCircle}>
        Agent is working on it…
      </Badge>
    )
  }
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {decision && <CategoryBadge category={decision.category} />}
      <QueueBadge queue={c.queue} />
      {decision && <Badge tone="tag">{routeLabel[decision.route]}</Badge>}
      <Link to={paths.case(id)} className="ml-1 text-sm font-medium text-link hover:text-link-hover">
        Open case
      </Link>
    </div>
  )
}
