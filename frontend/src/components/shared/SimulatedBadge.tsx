import { FlaskConical } from 'lucide-react'
import { Badge } from './Badge'

/** Marks refunds and messages as simulated (PLAN.md Scope): nothing really reaches a customer. */
export function SimulatedBadge() {
  return (
    <Badge tone="neutral" icon={FlaskConical} title="Simulated: no real money or message was sent">
      Simulated
    </Badge>
  )
}
