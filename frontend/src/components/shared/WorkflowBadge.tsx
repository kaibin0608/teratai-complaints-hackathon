import { Archive, CircleArrowUp, LoaderCircle, Search, type LucideIcon } from 'lucide-react'
import { workflowLabel } from '@/lib/labels'
import type { Workflow } from '@/lib/types'
import { Badge, type BadgeTone } from './Badge'

/** Bonus-platform workflow on top of the queue (Colour System §5: escalated = error, closed = neutral). */
const workflowStyle: Record<Workflow, { tone: BadgeTone; icon: LucideIcon }> = {
  escalated: { tone: 'error', icon: CircleArrowUp },
  reprocessing: { tone: 'info', icon: LoaderCircle },
  investigating: { tone: 'info', icon: Search },
  closed: { tone: 'neutral', icon: Archive },
}

export function WorkflowBadge({ workflow }: { workflow: Workflow }) {
  const { tone, icon } = workflowStyle[workflow]
  return (
    <Badge tone={tone} icon={icon}>
      {workflowLabel[workflow]}
    </Badge>
  )
}
