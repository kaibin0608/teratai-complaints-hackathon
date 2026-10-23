import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatMoney, formatMytDate } from '@/lib/format'
import { categoryLabel } from '@/lib/labels'
import type { CaseDetail } from '@/lib/types'

/**
 * What the language model read from the complaint. Code then resolved dates and found the transaction
 * from these clues, so this is where to look when a match looks wrong.
 */
export function CluesCard({ detail }: { detail: CaseDetail }) {
  const { clues, match } = detail
  if (!clues) return null
  const revised = match?.category_revised ? match.category : null

  return (
    <Card title="What the agent understood">
      <DetailList
        items={[
          {
            label: 'Category',
            value: revised ? (
              <>
                {categoryLabel[clues.category]} <span className="text-secondary">→ revised to {categoryLabel[revised]}</span>
              </>
            ) : (
              categoryLabel[clues.category]
            ),
          },
          { label: 'Language', value: clues.is_mixed_language ? 'Mixed English and Malay' : clues.language === 'MS' ? 'Malay' : 'English' },
          {
            label: 'Amount',
            value: clues.amount_mentioned && (
              <span className="tabular-nums">
                {formatMoney(clues.amount_mentioned)} <span className="text-secondary">{clues.amount_approximate ? '(approximate)' : '(exact)'}</span>
              </span>
            ),
          },
          { label: 'Other amounts', value: clues.other_amounts.length > 0 && clues.other_amounts.map(formatMoney).join(', ') },
          { label: 'Merchant / recipient', value: clues.counterparty_name },
          { label: 'Recipient bank', value: clues.counterparty_bank },
          { label: 'ATM location', value: clues.atm_location },
          {
            label: 'Date',
            value: clues.date_exact ? formatMytDate(clues.date_exact) : clues.date_phrase && <>“{clues.date_phrase}”</>,
          },
          { label: 'Card', value: clues.card_last4 && `•••• ${clues.card_last4}` },
          { label: 'Fee', value: [clues.fee_type, clues.fee_month].filter(Boolean).join(' · ') },
        ]}
      />
    </Card>
  )
}
