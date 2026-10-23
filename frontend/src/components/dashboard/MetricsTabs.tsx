import { BarCard, type BarItem } from '@/components/charts/BarCard'
import { TrendCard } from '@/components/charts/TrendCard'
import { Card } from '@/components/shared/Card'
import { formatCost, formatDuration, formatIsoTime, formatMoney, formatMs, formatPercent } from '@/lib/format'
import { categoryLabel, holdReasonLabel, outcomeLabel, routeLabel, workflowLabel } from '@/lib/labels'
import { CATEGORIES, HOLD_REASONS, OUTCOMES, PRIORITIES, ROUTES, WORKFLOWS, type Metrics } from '@/lib/types'
import { StatList } from './StatList'

/** A key the backend leaves out counts as zero (older servers omit newer hold reasons). */
const items = <K extends string>(keys: readonly K[], counts: Partial<Record<K, number>>, label: (key: K) => string): BarItem[] =>
  keys.map((key) => ({ label: label(key), value: counts[key] ?? 0 }))

const LANGUAGE = { EN: 'English', MS: 'Malay' } as const
const minutes = (value: number | null) => (value === null ? '–' : formatDuration(value * 60_000))

/** What the complaints are and where they go. */
export function OverviewTab({ m }: { m: Metrics }) {
  const { cases } = m
  return (
    <div className="flex flex-col gap-section">
      <TrendCard days={m.trends.received_by_day} />
      <div className="grid gap-section lg:grid-cols-2">
        <BarCard title="By category" subtitle="What customers complain about" items={items(CATEGORIES, cases.by_category, (k) => categoryLabel[k])} />
        <BarCard title="By outcome" subtitle="What the policy decided" items={items(OUTCOMES, cases.by_outcome, (k) => outcomeLabel[k])} />
        <BarCard title="By route" subtitle="Who handles it next" items={items(ROUTES, cases.by_route, (k) => routeLabel[k])} />
        <BarCard title="By priority" subtitle="After the 65+ rule" sort={false} items={items(PRIORITIES, cases.by_priority, (k) => k)} />
      </div>
    </div>
  )
}

/** How the agent is doing: quality, cost, speed, and why it asked for help. */
export function AgentTab({ m }: { m: Metrics }) {
  const { first_draft_failed: first, held_self_check_failed: held, human_edits_refused: refused } = m.self_check
  const { models, throughput } = m
  return (
    <div className="grid gap-section lg:grid-cols-2">
      <StatList
        title="Agent performance"
        stats={[
          { label: 'Self-check catches', value: first + held + refused, detail: `${first} first drafts · ${held} held · ${refused} human edits refused` },
          { label: 'Cost per complaint', value: formatCost(m.cost_myr.mean), detail: `p95 ${formatCost(m.cost_myr.p95)} · total ${formatCost(m.cost_myr.total)}` },
          { label: 'Speed per complaint', value: formatMs(m.latency_ms.p50), detail: `median · p95 ${formatMs(m.latency_ms.p95)}` },
          {
            label: 'Throughput',
            value: throughput.per_hour === null ? '–' : `${throughput.per_hour.toFixed(1)}/h`,
            detail:
              throughput.first_at && throughput.last_at
                ? `${throughput.decided} decided, ${formatIsoTime(throughput.first_at)} to ${formatIsoTime(throughput.last_at)}`
                : `${throughput.decided} decided`,
          },
        ]}
      />
      <Card title="Models used">
        <dl className="flex flex-col gap-3 text-sm">
          {[
            { step: 'Understanding the complaint', counts: models.extract },
            { step: 'Writing the reply', counts: models.draft },
          ].map(({ step, counts }) => (
            <div key={step}>
              <dt className="text-secondary">{step}</dt>
              <dd className="mt-1 flex flex-col gap-0.5 text-primary">
                {Object.keys(counts).length === 0 && <span className="text-secondary">None yet</span>}
                {Object.entries(counts).map(([model, count]) => (
                  <span key={model} className="tabular-nums">
                    {model} <span className="text-secondary">× {count}</span>
                  </span>
                ))}
              </dd>
            </div>
          ))}
        </dl>
      </Card>
      <BarCard title="Held for review" subtitle="Why the agent did not decide alone" items={items(HOLD_REASONS, m.holds.by_reason, (k) => holdReasonLabel[k])} />
      <BarCard
        title="Reply language"
       
        subtitle="The language of the reply"
        items={Object.entries(m.cases.by_language).map(([key, value]) => ({ label: LANGUAGE[key as keyof typeof LANGUAGE] ?? key, value }))}
      />
    </div>
  )
}

/** What people did with the cases, and the money (simulated). */
export function PeopleTab({ m }: { m: Metrics }) {
  const { cases, human, refunds_myr: refunds, sla } = m
  return (
    <div className="grid gap-section lg:grid-cols-2">
      <StatList
        title="People"
        stats={[
          { label: 'Turnaround', value: minutes(m.turnaround_minutes.p50), detail: `median, decision to closed · p95 ${minutes(m.turnaround_minutes.p95)}` },
          { label: 'SLA compliance', value: formatPercent(sla.compliance), detail: `${sla.closed} closed cases handled within their allowance` },
          { label: 'Fraud cases acknowledged', value: human.acknowledged, detail: 'holding reply sent to the customer' },
          { label: 'Under investigation', value: cases.by_workflow.investigating, detail: 'fraud cases the team is working' },
          { label: 'Agent re-running', value: cases.by_workflow.reprocessing, detail: 'sent back by a person' },
        ]}
      />
      <StatList
        title="Refunds (simulated)"
        stats={[
          { label: 'Awaiting approval', value: formatMoney(refunds.awaiting), detail: 'in open approval cases' },
          { label: 'Auto-paid', value: formatMoney(refunds.auto_paid), detail: 'small refunds the agent sent itself' },
          { label: 'Approved by people', value: formatMoney(refunds.approved_paid), detail: 'sent after an officer or manager approved' },
          { label: 'Rejected', value: formatMoney(refunds.rejected), detail: 'refunds a person declined to send' },
        ]}
      />
      <BarCard title="By workflow" subtitle="Cases touched by the ops platform" items={items(WORKFLOWS, cases.by_workflow, (k) => workflowLabel[k])} />
      <BarCard title="By channel" subtitle="Where complaints arrive" items={Object.entries(cases.by_channel).map(([label, value]) => ({ label, value }))} />
    </div>
  )
}
