import { ShieldCheck, ShieldX } from 'lucide-react'
import type { SelfCheckResult } from '@/lib/types'
import { Badge } from './Badge'

interface SelfCheckBadgeProps {
  result: SelfCheckResult
  /** Short label ("Passed" / "Flagged") where the context already says "self-check", e.g. a table column. */
  compact?: boolean
}

/** The code check that every transaction ID and amount in the reply is in the evidence. */
export function SelfCheckBadge({ result, compact = false }: SelfCheckBadgeProps) {
  const prefix = compact ? '' : 'Self-check '
  return result === 'passed' ? (
    <Badge tone="success" icon={ShieldCheck} title="Every ID and amount in the reply is in the evidence">
      {compact ? 'Passed' : `${prefix}passed`}
    </Badge>
  ) : (
    <Badge tone="error" icon={ShieldX} title="The reply mentions an ID or amount that is not in the evidence">
      {compact ? 'Flagged' : `${prefix}flagged`}
    </Badge>
  )
}
