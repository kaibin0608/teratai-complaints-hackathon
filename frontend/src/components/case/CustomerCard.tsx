import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { VulnerableBadge } from '@/components/shared/VulnerableBadge'
import { ageOn } from '@/lib/case'
import { formatMytDate } from '@/lib/format'
import type { CaseDetail } from '@/lib/types'

export function CustomerCard({ detail }: { detail: CaseDetail }) {
  const { customer, complaint, decision } = detail
  if (!customer) {
    return (
      <Card title="Customer">
        <p className="text-sm text-secondary">
          Customer <span className="font-medium text-primary">{complaint.customer_id}</span> is not in our records, so no
          transaction lookup was done.
        </p>
      </Card>
    )
  }

  return (
    <Card title="Customer" aside={decision?.vulnerable && <VulnerableBadge />}>
      <DetailList
        items={[
          { label: 'Name', value: customer.full_name },
          { label: 'Customer ID', value: customer.customer_id },
          {
            label: 'Age',
            value: `${ageOn(customer.date_of_birth, complaint.received_at)} on the received date (born ${formatMytDate(customer.date_of_birth)})`,
          },
          { label: 'Language', value: customer.preferred_language === 'MS' ? 'Malay (MS)' : 'English (EN)' },
          { label: 'Segment', value: customer.segment },
          { label: 'Location', value: [customer.city, customer.state].filter(Boolean).join(', ') },
          { label: 'Customer since', value: formatMytDate(customer.customer_since) },
        ]}
      />
      {customer.accounts.length > 0 && (
        <ul className="mt-3 divide-y divide-neutral-100 rounded-control border border-subtle text-sm">
          {customer.accounts.map((account) => (
            <li key={account.account_id} className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 py-2">
              <span className="text-primary">{account.product}</span>
              <span className="text-xs text-secondary tabular-nums">
                {account.account_id} · opened {formatMytDate(account.open_date)}
                {account.card_last4 && ` · card •••• ${account.card_last4}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
