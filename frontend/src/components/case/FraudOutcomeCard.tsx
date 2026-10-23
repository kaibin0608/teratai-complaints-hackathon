import { Badge, type BadgeTone } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatIsoTime } from '@/lib/format'
import { fraudOutcomeLabel } from '@/lib/labels'
import type { CaseDetail, FraudOutcome } from '@/lib/types'
import { useNameOf } from '@/hooks/useNameOf'

const outcomeTone: Record<FraudOutcome, BadgeTone> = {
  confirmed_fraud: 'error',
  not_fraud: 'success',
  recall_succeeded: 'success',
  recall_failed: 'warning',
}

/** How the fraud team closed the case. No message goes to the customer on this step. */
export function FraudOutcomeCard({ detail }: { detail: CaseDetail }) {
  const nameOf = useNameOf()
  const outcome = detail.fraud_outcome
  if (!outcome) return null
  return (
    <Card title="Fraud outcome" aside={<Badge tone={outcomeTone[outcome.outcome]}>{fraudOutcomeLabel[outcome.outcome]}</Badge>}>
      <DetailList
        items={[
          { label: 'Recorded by', value: nameOf(outcome.by) },
          { label: 'When', value: <span className="tabular-nums">{formatIsoTime(outcome.at)}</span> },
          { label: 'Reason', value: outcome.reason },
          { label: 'Proposed by', value: outcome.proposed_by && `${outcome.proposed_by} (the manager approved it)` },
        ]}
      />
    </Card>
  )
}
