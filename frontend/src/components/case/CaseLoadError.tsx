import { CircleAlert, RotateCw, SearchX } from 'lucide-react'
import { Link } from 'react-router'
import { ApiError } from '@/api/client'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { paths } from '@/lib/paths'

const backLink = (
  <Link to={paths.root} className="text-sm font-medium text-link hover:text-link-hover">
    Back to my queue
  </Link>
)

export function CaseLoadError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  const status = error instanceof ApiError ? error.status : null
  // The backend answers 404 both for an unknown ID and for another team's case.
  if (status === 404) {
    return (
      <StatusMessage icon={SearchX} title="Case not found" action={backLink}>
        It doesn't exist, or it isn't in your queue.
      </StatusMessage>
    )
  }
  return (
    <StatusMessage
      icon={CircleAlert}
      title="Could not load this case"
      action={
        <Button onClick={onRetry}>
          <RotateCw size={16} aria-hidden />
          Retry
        </Button>
      }
    >
      {error.message}
    </StatusMessage>
  )
}
