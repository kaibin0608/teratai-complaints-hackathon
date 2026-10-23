import type { ReactNode } from 'react'
import { formatCost, formatDuration, formatMoney, formatMs, formatPercent } from '@/lib/format'
import type { Metrics } from '@/lib/types'
import { Tile } from './Tile'

/** The manager's headline numbers (UI_API.md "Tile → Field"), in four groups by the question they answer. */
export function MetricTiles({ m }: { m: Metrics }) {
  const { approved, rejected, edited_and_approved: edited, override_rate, acknowledged } = m.human
  const decided = approved + rejected + edited
  const { first_draft_failed: first, held_self_check_failed: held, human_edits_refused: refused } = m.self_check
  const minutes = (value: number | null) => (value === null ? '–' : formatDuration(value * 60_000))

  return (
    <div className="flex flex-col gap-section">
      <Group title="Right now">
        <Tile
          label="Waiting for people"
          value={m.sla.open}
          detail={
            <>
              <span className={m.sla.overdue > 0 ? 'font-medium text-error-700' : undefined}>{m.sla.overdue} overdue</span>
              {' · '}
              <span className={m.sla.due_within_24h > 0 ? 'font-medium text-warning-800' : undefined}>{m.sla.due_within_24h} due in 24 h</span>
            </>
          }
        />
        <Tile label="Escalated to you" value={m.cases.by_workflow.escalated} detail="waiting for the manager's decision" />
        <Tile label="Under investigation" value={m.cases.by_workflow.investigating} detail="fraud cases the team is working" />
        <Tile label="Agent re-running" value={m.cases.by_workflow.reprocessing} detail="sent back by a person" />
      </Group>

      <Group title="The agent">
        <Tile label="Auto-resolved" value={formatPercent(m.auto_resolve_rate)} detail={`of ${m.cases.total} complaints, no human needed`} />
        <Tile label="Self-check catches" value={first + held + refused} detail={`${first} first drafts · ${held} held · ${refused} human edits refused`} />
        <Tile label="Cost per complaint" value={formatCost(m.cost_myr.mean)} detail={`p95 ${formatCost(m.cost_myr.p95)} · total ${formatCost(m.cost_myr.total)}`} />
        <Tile label="Speed per complaint" value={formatMs(m.latency_ms.p50)} detail={`median · p95 ${formatMs(m.latency_ms.p95)}`} />
      </Group>

      <Group title="People">
        <Tile
          label="Override rate"
          value={formatPercent(override_rate)}
          detail={decided === 0 ? 'no human decisions yet' : `people changed the agent on ${rejected + edited} of ${decided}`}
        />
        <Tile label="Turnaround" value={minutes(m.turnaround_minutes.p50)} detail={`median, decision to closed · p95 ${minutes(m.turnaround_minutes.p95)}`} />
        <Tile label="Fraud cases acknowledged" value={acknowledged} detail="holding reply sent to the customer" />
        <Tile label="SLA compliance" value={formatPercent(m.sla.compliance)} detail={`${m.sla.closed} closed cases handled within their allowance`} />
      </Group>

      <Group title="Refunds (simulated)">
        <Tile label="Awaiting approval" value={formatMoney(m.refunds_myr.awaiting)} detail="in open approval cases" />
        <Tile label="Auto-paid" value={formatMoney(m.refunds_myr.auto_paid)} detail="small refunds the agent sent itself" />
        <Tile label="Approved by people" value={formatMoney(m.refunds_myr.approved_paid)} detail="sent after an officer or manager approved" />
        <Tile label="Rejected" value={formatMoney(m.refunds_myr.rejected)} detail="refunds a person declined to send" />
      </Group>
    </div>
  )
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 font-sans text-xs font-medium tracking-wide text-secondary uppercase">{title}</h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{children}</div>
    </section>
  )
}
