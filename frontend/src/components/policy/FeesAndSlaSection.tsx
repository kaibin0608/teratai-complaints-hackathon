import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { formatMoney } from '@/lib/format'
import type { FeeRow, SlaRow } from '@/lib/policy'
import { PolicySection } from './PolicySection'
import { PolicyTable, type Column } from './PolicyTable'

const plural = (n: number, unit: string) => `${n} ${unit}${n === 1 ? '' : 's'}`

const FEE_COLUMNS: readonly Column<FeeRow>[] = [
  { head: 'Fee', render: (f) => f.fee },
  { head: 'Product', render: (f) => f.product },
  { head: 'Amount', render: (f) => <span className="tabular-nums">{formatMoney(f.amount)}</span> },
  { head: 'Waiver', render: (f) => (f.waiver === 'None' ? 'No waiver' : f.waiver) },
]

const SLA_COLUMNS: readonly Column<SlaRow>[] = [
  { head: 'Priority', render: (s) => <PriorityBadge priority={s.priority} /> },
  { head: 'Acknowledge within', render: (s) => plural(s.acknowledgeHours, 'hour') },
  { head: 'Resolve within', render: (s) => plural(s.resolveBusinessDays, 'business day') },
]

/** What each fee should be (the basis for fee-dispute refunds) and how fast each priority must be handled. */
export function FeesAndSlaSection({ fees, sla }: { fees: readonly FeeRow[]; sla: readonly SlaRow[] }) {
  return (
    <>
      <PolicySection id="fees" title="Fee schedule" description="The fee that is due. A fee dispute is refunded the amount charged minus the amount due, after the waiver.">
        <PolicyTable columns={FEE_COLUMNS} rows={fees} rowKey={(f) => f.code} />
      </PolicySection>

      <PolicySection id="sla" title="Service levels" description="The time allowed to acknowledge a case and to resolve it. Case timers count against these.">
        <PolicyTable columns={SLA_COLUMNS} rows={sla} rowKey={(s) => s.priority} />
      </PolicySection>
    </>
  )
}
