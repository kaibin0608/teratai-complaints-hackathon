import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { formatCost, formatIsoTime, formatMs } from '@/lib/format'
import { holdReasonLabel, outcomeLabel, routeLabel } from '@/lib/labels'
import type { CaseDetail } from '@/lib/types'

/**
 * Every time the agent worked on this case. Run 1 is the agent's own decision: it never changes and is what
 * predictions.csv scores. Later runs come from "send back" and are what the page shows.
 */
export function RunsCard({ detail }: { detail: CaseDetail }) {
  const { runs, case: c } = detail
  if (runs.length < 2) return null
  return (
    <Card title="Agent runs" aside={<span className="text-xs text-secondary">{runs.length}</span>}>
      <ol className="divide-y divide-neutral-100 rounded-control border border-subtle text-sm">
        {runs.map((run, index) => (
          <li key={run.run_id} className="flex flex-col gap-1 px-3 py-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-medium text-primary">Run {index + 1}</span>
              <Badge tone="tag">{run.run_kind === 'autonomous' ? 'Autonomous' : 'After send back'}</Badge>
              {run.run_id === c.autonomous_run_id && <Badge tone="brand">Scored</Badge>}
              {run.run_id === c.current_run_id && <Badge tone="info">Shown on this page</Badge>}
            </div>
            <p className="text-body">
              {run.outcome ? outcomeLabel[run.outcome] : 'No decision'}
              {run.route && ` → ${routeLabel[run.route]}`}
              {run.hold_reason && ` · held: ${holdReasonLabel[run.hold_reason]}`}
            </p>
            <p className="text-xs text-secondary tabular-nums">
              {formatIsoTime(run.created_at)} · {formatCost(run.cost_myr)} · {formatMs(run.latency_ms)}
            </p>
          </li>
        ))}
      </ol>
    </Card>
  )
}
