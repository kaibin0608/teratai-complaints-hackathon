import type { ReactNode } from 'react'
import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { DetailList, type Detail } from '@/components/shared/DetailList'
import { mytToMs } from '@/lib/clock'
import { formatIsoTime, formatMoney, formatMytDate } from '@/lib/format'
import type { CaseDetail, Decision, Evidence, TxnRow } from '@/lib/types'

/** The matched transaction and the facts the decision used, by category. */
export function EvidenceCard({ detail }: { detail: CaseDetail }) {
  const { evidence, decision } = detail
  if (!evidence || !decision) return null
  const txn = evidence.matched_txn

  let body: ReactNode
  if (decision.category === 'SERVICE_QUALITY') body = <Note>No transaction involved: a service complaint.</Note>
  else if (!txn) body = <Note>No transaction matched the complaint.</Note>
  else
    body = (
      <div className="flex flex-col gap-3">
        <CategoryEvidence detail={detail} evidence={evidence} decision={decision} txn={txn} />
        {decision.category !== 'DUPLICATE_CHARGE' && evidence.related_txns.length > 0 && <RelatedTransactions rows={evidence.related_txns} />}
      </div>
    )

  return (
    <Card title="Evidence" aside={txn && <span className="text-xs text-secondary tabular-nums">{txn.txn_id}</span>}>
      {body}
    </Card>
  )
}

interface VariantProps {
  detail: CaseDetail
  evidence: Evidence
  decision: Decision
  txn: TxnRow
}

function CategoryEvidence(props: VariantProps) {
  switch (props.decision.category) {
    case 'DUPLICATE_CHARGE':
      return <DuplicateEvidence {...props} />
    case 'FAILED_TRANSFER':
      return <TransferEvidence {...props} />
    case 'ATM_NOT_DISPENSED':
      return <AtmEvidence {...props} />
    case 'UNAUTHORISED_CARD':
      return <CardEvidence {...props} />
    case 'FEE_DISPUTE':
      return <FeeEvidence {...props} />
    default:
      return <DetailList items={txnFacts(props.txn)} />
  }
}

function DuplicateEvidence({ evidence, decision, txn }: VariantProps) {
  const earlier = evidence.related_txns[0]
  return (
    <div className="flex flex-col gap-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Panel title="Earlier charge">
          {earlier ? <DetailList items={txnFacts(earlier)} /> : <Note>No earlier identical charge found.</Note>}
        </Panel>
        <Panel title="Disputed (later) charge">
          <DetailList items={txnFacts(txn)} />
        </Panel>
      </div>
      {earlier && <p className="text-sm text-body">{formatGap(mytToMs(txn.time) - mytToMs(earlier.time))} apart.</p>}
      {evidence.reversal ? (
        <p className="text-sm text-warning-800">
          Already reversed by {evidence.reversal.txn_id} on {formatIsoTime(evidence.reversal.time)}.
        </p>
      ) : (
        decision.rule_id === 'DUP.ALREADY_REVERSED' && <p className="text-sm text-warning-800">One of the charges was already reversed.</p>
      )}
    </div>
  )
}

function TransferEvidence({ evidence, txn }: VariantProps) {
  const failed = txn.status === 'Failed'
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        <Badge tone={failed ? 'error' : 'success'}>{failed ? 'Transfer failed' : 'Transfer completed: reached the recipient'}</Badge>
        <Badge tone={evidence.reversal ? 'info' : 'neutral'}>
          {evidence.reversal
            ? `Reversed by ${evidence.reversal.txn_id} on ${formatIsoTime(evidence.reversal.time)}`
            : 'No reversal found'}
        </Badge>
      </div>
      <DetailList items={txnFacts(txn)} />
    </div>
  )
}

function AtmEvidence({ evidence, decision, txn }: VariantProps) {
  const journal = evidence.atm_journal
  return (
    <div className="flex flex-col gap-3">
      {journal ? (
        <Panel title="ATM journal">
          <DetailList
            items={[
              { label: 'Requested', value: formatMoney(journal.requested_myr) },
              { label: 'Dispensed', value: <span className="font-medium">{formatMoney(journal.dispensed_myr)}</span> },
              { label: 'Shortfall', value: decision.calculation.inputs.shortfall && formatMoney(decision.calculation.inputs.shortfall) },
              { label: 'Journal status', value: journal.journal_status },
              { label: 'ATM', value: `${journal.atm_id} · ${journal.atm_location}` },
            ]}
          />
        </Panel>
      ) : (
        <Note>No ATM journal entry for this withdrawal.</Note>
      )}
      <DetailList items={txnFacts(txn)} />
    </div>
  )
}

/** Strong authentication means the cardholder approved it: the policy sends these to the fraud team. */
const AUTH_MEANING: Record<string, string> = {
  None: 'No strong authentication: card not present.',
  '3DS-OTP': 'Approved with a one-time password: strong authentication.',
  'Chip+PIN': 'Chip and PIN: strong authentication.',
}

function CardEvidence({ txn }: VariantProps) {
  const overseas = txn.merchant_country && txn.merchant_country !== 'MY'
  return (
    <div className="flex flex-col gap-3">
      <Panel title="Authentication">
        <p className="font-display text-xl font-semibold text-primary">{txn.auth_method || 'Unknown'}</p>
        <p className="mt-0.5 text-sm text-secondary">
          {AUTH_MEANING[txn.auth_method] ?? 'An authentication method the policy does not cover.'}
        </p>
      </Panel>
      {overseas && <Badge tone="warning">Overseas merchant: {txn.merchant_country}</Badge>}
      <DetailList items={txnFacts(txn)} />
    </div>
  )
}

function FeeEvidence({ detail, evidence, txn }: VariantProps) {
  const fee = evidence.fee_schedule_row
  const account = detail.customer?.accounts.find((a) => a.account_id === txn.account_id)
  return (
    <div className="flex flex-col gap-3">
      <DetailList items={txnFacts(txn)} />
      {fee ? (
        <Panel title="Fee schedule">
          <DetailList
            items={[
              { label: 'Fee', value: fee.fee_name },
              { label: 'Product', value: fee.product },
              { label: 'Scheduled', value: formatMoney(fee.amount_myr) },
              { label: 'Waiver rule', value: fee.waiver_rule },
            ]}
          />
        </Panel>
      ) : (
        <Note>No fee-schedule row matched this fee.</Note>
      )}
      {account && (
        <DetailList
          items={[
            { label: 'Account', value: `${account.product} · ${account.account_id}` },
            { label: 'Opened', value: formatMytDate(account.open_date) },
          ]}
        />
      )}
    </div>
  )
}

/** Other transactions the decision used (anything beyond the matched one). */
function RelatedTransactions({ rows }: { rows: readonly TxnRow[] }) {
  return (
    <Panel title="Related transactions">
      <ul className="flex flex-col gap-2 text-sm">
        {rows.map((row) => (
          <li key={row.txn_id} className="flex flex-wrap items-baseline justify-between gap-x-3">
            <span className="text-primary tabular-nums">
              {row.txn_id} · {row.merchant_or_counterparty || row.channel}
            </span>
            <span className="text-xs text-secondary tabular-nums">
              {formatIsoTime(row.time)} · {formatMoney(row.amount_myr)} · {row.status}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

/** The transaction row as label/value pairs; empty CSV fields are skipped. */
function txnFacts(txn: TxnRow): Detail[] {
  return [
    { label: 'Transaction', value: <span className="tabular-nums">{txn.txn_id}</span> },
    { label: 'Time', value: <span className="tabular-nums">{formatIsoTime(txn.time)}</span> },
    { label: 'Amount', value: <span className="font-medium tabular-nums">{formatMoney(txn.amount_myr)}</span> },
    { label: 'Channel', value: txn.channel },
    { label: 'Merchant / to', value: txn.merchant_or_counterparty },
    { label: 'Recipient account', value: txn.counterparty_account },
    { label: 'Recipient bank', value: txn.counterparty_bank },
    { label: 'Card', value: txn.card_last4 && `•••• ${txn.card_last4}` },
    { label: 'Status', value: txn.status },
    { label: 'Description', value: txn.description },
  ]
}

/** "1m 50s", "3h 4m": the exact gap between two charges. */
function formatGap(ms: number): string {
  const seconds = Math.round(Math.abs(ms) / 1000)
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-control border border-subtle p-3">
      <h3 className="mb-2 font-sans text-xs font-medium tracking-wide text-secondary uppercase">{title}</h3>
      {children}
    </div>
  )
}

function Note({ children }: { children: ReactNode }) {
  return <p className="text-sm text-secondary">{children}</p>
}
