import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { fraudOutcomeLabel, outcomeLabel } from '@/lib/labels'
import { FRAUD_OUTCOMES, type CaseDetail, type FraudOutcome, type Outcome } from '@/lib/types'

const finalLabel = (outcome: NonNullable<CaseDetail['final']>['outcome']): string => {
  if (outcome === null) return '—'
  if (outcome === 'REJECTED') return 'Rejected'
  if ((FRAUD_OUTCOMES as readonly string[]).includes(outcome)) return fraudOutcomeLabel[outcome as FraudOutcome]
  return outcomeLabel[outcome as Outcome]
}

/** The agent's own decision (never changed) beside what people did. Shown once a person has acted. */
export function AgentVsHumanCard({ detail }: { detail: CaseDetail }) {
  const { autonomous, final, differs } = detail
  if (!autonomous || !final) return null
  const reason = detail.case.human_action?.reason
  const changed = differs.decision || differs.refund || differs.reply

  return (
    <Card title="Agent vs people" aside={<Badge tone={changed ? 'warning' : 'success'}>{changed ? 'People changed the agent' : 'Same as the agent'}</Badge>}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Column
          title="Agent (autonomous)"
          items={[
            { label: 'Outcome', value: outcomeLabel[autonomous.outcome] },
            { label: 'Refund', value: formatMoney(autonomous.refund_amount_myr) },
            { label: 'Transaction', value: autonomous.matched_txn_id },
          ]}
        />
        <Column
          title={`${final.by} (${final.action.replace(/_/g, ' ')})`}
          items={[
            { label: 'Outcome', value: finalLabel(final.outcome), changed: differs.decision },
            { label: 'Refund', value: formatMoney(final.refund_amount_myr), changed: differs.refund },
            { label: 'Reply', value: final.sent ? 'Sent (simulated)' : 'Not sent', changed: differs.reply },
            { label: 'Reason', value: reason ?? null },
            { label: 'When', value: formatIsoTime(final.at) },
          ]}
        />
      </div>
      {differs.reply && final.reply_text && (
        <details className="mt-3">
          <summary className="cursor-pointer text-sm text-link select-none hover:text-link-hover">Compare the replies</summary>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            <ReplyBox title="Agent's reply" text={autonomous.reply_text} />
            <ReplyBox title="Reply that went out" text={final.reply_text} />
          </div>
        </details>
      )}
    </Card>
  )
}

function Column({ title, items }: { title: string; items: { label: string; value: string | null; changed?: boolean }[] }) {
  return (
    <div className="rounded-control border border-subtle p-3">
      <h3 className="mb-2 font-sans text-xs font-medium tracking-wide text-secondary uppercase">{title}</h3>
      <DetailList
        items={items.map(({ label, value, changed }) => ({
          label,
          value: value && (changed ? <span className="rounded-badge bg-warning-50 px-1 font-medium text-warning-800">{value}</span> : value),
        }))}
      />
    </div>
  )
}

function ReplyBox({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h4 className="mb-1 text-xs font-medium text-secondary">{title}</h4>
      <p className="rounded-control bg-subtle px-3 py-2 text-sm whitespace-pre-line text-body">{text}</p>
    </div>
  )
}
