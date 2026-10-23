import {
  CircleCheck,
  CircleX,
  Clock,
  LoaderCircle,
  Send,
  ShieldAlert,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { queueLabel } from '@/lib/labels'
import type { Queue } from '@/lib/types'
import { Badge, type BadgeTone } from './Badge'

/** Where the case is (the contract's case_state, plus processing/error), as Colour System §5 roles. */
const queueStyle: Record<Queue, { tone: BadgeTone; icon: LucideIcon }> = {
  processing: { tone: 'info', icon: LoaderCircle },
  error: { tone: 'error', icon: TriangleAlert },
  auto_resolved: { tone: 'success', icon: Send },
  awaiting_approval: { tone: 'info', icon: Clock },
  with_fraud_team: { tone: 'info', icon: ShieldAlert },
  approved: { tone: 'success', icon: CircleCheck },
  rejected: { tone: 'error', icon: CircleX },
}

export function QueueBadge({ queue }: { queue: Queue }) {
  const { tone, icon } = queueStyle[queue]
  return (
    <Badge tone={tone} icon={icon}>
      {queueLabel[queue]}
    </Badge>
  )
}
