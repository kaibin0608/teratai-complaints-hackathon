import { ChevronUp, ChevronsUp, Minus } from 'lucide-react'
import type { Priority } from '@/lib/types'
import { Badge } from './Badge'

/** Colour System §5: P1 solid error · P2 warning · P3 info. */
export function PriorityBadge({ priority }: { priority: Priority }) {
  switch (priority) {
    case 'P1':
      return (
        <Badge tone="error" solid icon={ChevronsUp} title="Priority 1">
          P1
        </Badge>
      )
    case 'P2':
      return (
        <Badge tone="warning" icon={ChevronUp} title="Priority 2">
          P2
        </Badge>
      )
    case 'P3':
      return (
        <Badge tone="info" icon={Minus} title="Priority 3">
          P3
        </Badge>
      )
  }
}
