import { CircleAlert, LoaderCircle, RotateCw } from 'lucide-react'
import { Button } from '@/components/shared/Button'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useMetrics } from '@/hooks/useMetrics'
import { formatCost, formatMoney, formatMs, formatPercent } from '@/lib/format'
import type { Metrics } from '@/lib/types'
import { Tile } from './Tile'

/** The manager's headline numbers (UI_API.md "Tile → Field"), measured on the demo clock. */
export function MetricTiles() {
  const result = useMetrics()
  if (result.status === 'loading') return <StatusMessage busy icon={LoaderCircle} title="Loading the numbers…" />
  if (result.status === 'error') {
    return (
      <StatusMessage
        icon={CircleAlert}
        title="Could not load the dashboard numbers"
        action={
          <Button onClick={result.reload}>
            <RotateCw size={16} aria-hidden />
            Retry
          </Button>
        }
      >
        {result.error.message}
      </StatusMessage>
    )
  }
  const m = result.data
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <WaitingTile m={m} />
      <Tile label="Escalated to you" value={m.cases.by_workflow.escalated} detail="waiting for the manager's decision" />
      <Tile label="Auto-resolved" value={formatPercent(m.auto_resolve_rate)} detail={`of ${m.cases.total} complaints, no human needed`} />
      <OverrideTile m={m} />
      <SelfCheckTile m={m} />
      <Tile
        label="SLA compliance"
        value={formatPercent(m.sla.compliance)}
        detail={`${m.sla.closed} closed cases handled within their allowance`}
      />
      <Tile
        label="Cost per complaint"
        value={formatCost(m.cost_myr.mean)}
        detail={`p95 ${formatCost(m.cost_myr.p95)} · total ${formatCost(m.cost_myr.total)}`}
      />
      <Tile label="Speed per complaint" value={formatMs(m.latency_ms.p50)} detail={`median · p95 ${formatMs(m.latency_ms.p95)}`} />
      <Tile
        label="Refunds awaiting approval"
        value={formatMoney(m.refunds_myr.awaiting)}
        detail={`auto-paid ${formatMoney(m.refunds_myr.auto_paid)} · approved ${formatMoney(m.refunds_myr.approved_paid)}`}
      />
    </div>
  )
}

function WaitingTile({ m }: { m: Metrics }) {
  return (
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
  )
}

function OverrideTile({ m }: { m: Metrics }) {
  const { approved, rejected, edited_and_approved: edited, override_rate } = m.human
  const decided = approved + rejected + edited
  return (
    <Tile
      label="Override rate"
      value={formatPercent(override_rate)}
      detail={decided === 0 ? 'no human decisions yet' : `people changed the agent on ${rejected + edited} of ${decided}`}
    />
  )
}

function SelfCheckTile({ m }: { m: Metrics }) {
  const { first_draft_failed: first, held_self_check_failed: held, human_edits_refused: edits } = m.self_check
  return (
    <Tile
      label="Self-check catches"
      value={first + held + edits}
      detail={`${first} first drafts · ${held} held · ${edits} human edits refused`}
    />
  )
}
