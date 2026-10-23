import { ArrowRight, CircleAlert, CircleCheck, Clock, Flag, TriangleAlert, type LucideIcon } from 'lucide-react'
import { Link } from 'react-router'
import { mytToMs, slaNowMs } from '@/lib/clock'
import { cx } from '@/lib/cx'
import { formatDuration } from '@/lib/format'
import { paths } from '@/lib/paths'
import { summariseWork } from '@/lib/workload'
import { useMetrics } from '@/hooks/useMetrics'
import { useOpenWork } from '@/hooks/useOpenWork'

interface Row {
  icon: LucideIcon
  tone: 'error' | 'warning'
  text: string
  detail?: string
  cta: string
  to: string
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`

/**
 * What needs the manager right now, and nothing else: the list is empty (and says so) when all is well.
 * Every row is a way in: it opens the exact cases behind the number.
 */
export function NeedsYou() {
  const work = useOpenWork()
  const metrics = useMetrics()
  if (work.status !== 'success') return null

  const nowMs = slaNowMs()  // deadlines on the complaints' calendar (lib/clock.ts)
  const summary = summariseWork(work.data.items, nowMs)
  const escalated = work.data.workflow_counts?.escalated ?? 0
  const failed = metrics.status === 'success' ? metrics.data.cases.by_queue.error : 0
  const oldest = summary.overdue[0]

  const candidates: (Row | false)[] = [
    escalated > 0 && {
      icon: CircleAlert,
      tone: 'error',
      text: `${plural(escalated, 'case is', 'cases are')} escalated and waiting for your decision`,
      cta: 'Decide',
      to: '#escalated',
    },
    summary.unownedSensitive.length > 0 && {
      icon: Flag,
      tone: 'warning',
      text: `${plural(summary.unownedSensitive.length, 'sensitive case has', 'sensitive cases have')} nobody assigned`,
      cta: 'Assign',
      to: `${paths.cases}?sensitive=1&assigned=none`,
    },
    summary.overdue.length > 0 && {
      icon: Clock,
      tone: 'warning',
      text: `${plural(summary.overdue.length, 'open case is', 'open cases are')} past the deadline`,
      detail: oldest?.resolve_due_at ? `The oldest was due ${formatDuration(nowMs - mytToMs(oldest.resolve_due_at))} ago.` : undefined,
      cta: 'Open',
      to: paths.cases,
    },
    failed > 0 && {
      icon: TriangleAlert,
      tone: 'error',
      text: `The agent could not finish ${plural(failed, 'case', 'cases')}`,
      cta: 'Open',
      to: `${paths.cases}?queue=error`,
    },
  ]
  const rows = candidates.filter((row): row is Row => row !== false)

  if (rows.length === 0) {
    return (
      <p className="flex items-center gap-2 rounded-card border border-success-200 bg-success-50 px-card py-3 text-sm text-success-800">
        <CircleCheck size={16} aria-hidden className="text-success-500" />
        All clear. Nothing needs your decision right now.
      </p>
    )
  }

  return (
    <section aria-label="Needs you" className="rounded-card border border-default bg-card">
      <header className="border-b border-subtle px-card py-2.5">
        <h2 className="text-sm font-semibold">Needs you</h2>
      </header>
      <ul className="divide-y divide-neutral-100">
        {rows.map((row) => {
          const Icon = row.icon
          const link = 'text-sm font-medium text-link hover:text-link-hover'
          return (
            <li key={row.text} className="flex items-center gap-3 px-card py-2.5">
              <Icon size={16} aria-hidden className={cx('shrink-0', row.tone === 'error' ? 'text-error-500' : 'text-warning-500')} />
              <p className="min-w-0 flex-1 text-sm text-primary">
                {row.text}
                {row.detail && <span className="text-secondary"> · {row.detail}</span>}
              </p>
              {row.to.startsWith('#') ? (
                <a href={row.to} className={cx(link, 'flex items-center gap-1')}>
                  {row.cta} <ArrowRight size={14} aria-hidden />
                </a>
              ) : (
                <Link to={row.to} className={cx(link, 'flex items-center gap-1')}>
                  {row.cta} <ArrowRight size={14} aria-hidden />
                </Link>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
