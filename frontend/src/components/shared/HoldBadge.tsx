import { CirclePause } from 'lucide-react'
import { holdReasonLabel } from '@/lib/labels'
import type { HoldReason } from '@/lib/types'
import { Badge } from './Badge'

/** Why the agent held a case for a human (Colour System §5: warning = on hold). */
export function HoldBadge({ reason }: { reason: HoldReason }) {
  return (
    <Badge tone="warning" icon={CirclePause} title={`Held: ${holdReasonLabel[reason]}`}>
      {holdReasonLabel[reason]}
    </Badge>
  )
}
