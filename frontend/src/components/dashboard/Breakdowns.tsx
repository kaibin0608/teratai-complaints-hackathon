import { BarCard, type BarItem } from '@/components/charts/BarCard'
import { Card } from '@/components/shared/Card'
import { TrendCard } from '@/components/charts/TrendCard'
import { formatIsoTime } from '@/lib/format'
import { categoryLabel, holdReasonLabel, outcomeLabel, routeLabel, workflowLabel } from '@/lib/labels'
import { CATEGORIES, HOLD_REASONS, OUTCOMES, PRIORITIES, ROUTES, WORKFLOWS, type Metrics } from '@/lib/types'

const items = <K extends string>(keys: readonly K[], counts: Record<K, number>, label: (key: K) => string): BarItem[] =>
  keys.map((key) => ({ label: label(key), value: counts[key] }))

const LANGUAGE = { EN: 'English', MS: 'Malay' } as const

/** What the complaints are, where they go and how they end: one chart per breakdown the backend returns. */
export function Breakdowns({ m }: { m: Metrics }) {
  const { cases } = m
  return (
    <section className="flex flex-col gap-section">
      <h2 className="font-sans text-xs font-medium tracking-wide text-secondary uppercase">Breakdowns</h2>
      <TrendCard days={m.trends.received_by_day} />
      <div className="grid gap-section lg:grid-cols-2">
        <BarCard title="By category" subtitle="What customers complain about" items={items(CATEGORIES, cases.by_category, (k) => categoryLabel[k])} />
        <BarCard title="By outcome" subtitle="What the policy decided" items={items(OUTCOMES, cases.by_outcome, (k) => outcomeLabel[k])} />
        <BarCard title="By route" subtitle="Who handles it next" items={items(ROUTES, cases.by_route, (k) => routeLabel[k])} />
        <BarCard title="By priority" subtitle="After the 65+ rule" sort={false} items={items(PRIORITIES, cases.by_priority, (k) => k)} />
        <BarCard title="Held for review" subtitle="Why the agent did not decide alone" items={items(HOLD_REASONS, m.holds.by_reason, (k) => holdReasonLabel[k])} />
        <BarCard title="By workflow" subtitle="Cases touched by the ops platform" items={items(WORKFLOWS, cases.by_workflow, (k) => workflowLabel[k])} />
        <BarCard title="By channel" subtitle="Where complaints arrive" items={Object.entries(cases.by_channel).map(([label, value]) => ({ label, value }))} />
        <BarCard title="Reply language" subtitle="The language of the reply" items={Object.entries(cases.by_language).map(([key, value]) => ({ label: LANGUAGE[key as keyof typeof LANGUAGE] ?? key, value }))} />
      </div>
      <ActivityCard models={m.models} throughput={m.throughput} />
    </section>
  )
}

/** Which models did the work, and how fast the agent has been deciding. */
function ActivityCard({ models, throughput }: { models: Metrics['models']; throughput: Metrics['throughput'] }) {
  const steps = [
    { step: 'Understanding the complaint', counts: models.extract },
    { step: 'Writing the reply', counts: models.draft },
  ]
  return (
    <Card title="Agent activity">
      <dl className="grid gap-3 text-sm sm:grid-cols-3">
        {steps.map(({ step, counts }) => (
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
        <div>
          <dt className="text-secondary">Throughput</dt>
          <dd className="mt-1 flex flex-col gap-0.5 text-primary tabular-nums">
            <span>{throughput.decided} decided</span>
            <span className="text-secondary">{throughput.per_hour === null ? '– per hour' : `${throughput.per_hour.toFixed(1)} per hour`}</span>
            {throughput.first_at && throughput.last_at && (
              <span className="text-xs text-secondary">
                {formatIsoTime(throughput.first_at)} to {formatIsoTime(throughput.last_at)}
              </span>
            )}
          </dd>
        </div>
      </dl>
    </Card>
  )
}
