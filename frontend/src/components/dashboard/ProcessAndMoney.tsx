import { formatDuration, formatMoney, formatPercent } from '@/lib/format'
import type { Metrics } from '@/lib/types'
import { StatList } from './StatList'

const minutes = (value: number | null) => (value === null ? '–' : formatDuration(value * 60_000))

/** Money moved or waiting, all simulated: nothing really leaves the system. */
export function MoneyCard({ m }: { m: Metrics }) {
  const { refunds_myr: refunds } = m
  return (
    <StatList
      title="Refunds (simulated)"
      stats={[
        { label: 'Awaiting approval', value: formatMoney(refunds.awaiting), detail: 'in open approval cases' },
        { label: 'Auto-paid', value: formatMoney(refunds.auto_paid), detail: 'small refunds the agent sent itself' },
        { label: 'Approved by people', value: formatMoney(refunds.approved_paid), detail: 'sent after an officer or manager approved' },
        { label: 'Rejected', value: formatMoney(refunds.rejected), detail: 'refunds a person declined to send' },
      ]}
    />
  )
}

/** Is the process healthy: does the agent need help often, and are cases closed on time. */
export function ProcessCard({ m }: { m: Metrics }) {
  const { first_draft_failed: first, held_self_check_failed: held, human_edits_refused: refused } = m.self_check
  return (
    <StatList
      title="How the process is doing"
      stats={[
        { label: 'Held for review', value: m.holds.total, detail: 'cases the agent would not decide alone' },
        { label: 'Self-check catches', value: first + held + refused, detail: `${first} first drafts · ${held} held · ${refused} human edits refused` },
        { label: 'Turnaround', value: minutes(m.turnaround_minutes.p50), detail: 'median, decision to closed' },
        { label: 'SLA compliance', value: formatPercent(m.sla.compliance), detail: `${m.sla.closed} closed cases handled within their allowance` },
      ]}
    />
  )
}
