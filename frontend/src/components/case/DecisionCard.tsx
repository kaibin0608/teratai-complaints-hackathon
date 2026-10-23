import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatMoney } from '@/lib/format'
import { categoryLabel, outcomeLabel, routeLabel } from '@/lib/labels'
import type { CaseDetail } from '@/lib/types'

/** What the agent decided and why: the rule, and the working behind the refund. */
export function DecisionCard({ detail }: { detail: CaseDetail }) {
  const { decision, complaint, clues } = detail
  if (!decision) return null

  const heldRoute = decision.policy_route !== decision.route
  const staffNote = complaint.channel === 'Call centre note'
  const language = decision.reply_language === 'MS' ? 'Malay (MS)' : 'English (EN)'
  const languageWhy = staffNote
    ? "a call-centre note, so the customer's preferred language"
    : clues?.is_mixed_language
      ? "mixed language, so the customer's preferred language"
      : 'the language of the complaint'

  return (
    <Card title="Decision">
      <p className="font-display text-2xl font-semibold text-primary tabular-nums">
        {outcomeLabel[decision.outcome]}
        {decision.outcome === 'REFUND' && <span className="ml-2">{formatMoney(decision.refund_amount_myr)}</span>}
      </p>

      {decision.calculation.explanation && (
        <p className="mt-2 rounded-control bg-subtle px-3 py-2 text-sm text-body tabular-nums">
          {decision.calculation.explanation}
        </p>
      )}

      <div className="mt-3">
        <DetailList
          items={[
            { label: 'Category', value: categoryLabel[decision.category] },
            { label: 'Rule', value: <span className="text-sm tabular-nums">{decision.rule_id}</span> },
            {
              label: 'Route',
              value: heldRoute ? (
                <>
                  {routeLabel[decision.route]}{' '}
                  <span className="text-secondary">(policy said {routeLabel[decision.policy_route]}; held for review)</span>
                </>
              ) : (
                routeLabel[decision.route]
              ),
            },
            {
              label: 'Priority',
              value: decision.vulnerable ? `${decision.priority}, raised one level: customer is 65+` : decision.priority,
            },
            { label: 'Reply language', value: `${language}: ${languageWhy}` },
          ]}
        />
      </div>
    </Card>
  )
}
