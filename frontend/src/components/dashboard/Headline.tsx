import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { formatMoney, formatPercent } from '@/lib/format'
import { paths } from '@/lib/paths'
import type { Metrics } from '@/lib/types'

/** The four numbers a manager checks first, in one strip. Colour appears only where something needs attention. */
export function Headline({ m }: { m: Metrics }) {
  const { sla, human, refunds_myr: refunds } = m
  const decided = human.approved + human.rejected + human.edited_and_approved
  const calm = sla.overdue === 0 && sla.due_within_24h === 0

  return (
    <section
      aria-label="Headline numbers"
      className="grid divide-y divide-neutral-100 rounded-card border border-default bg-card sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4 xl:divide-x"
    >
      <Figure label="Open cases" value={sla.open} to={paths.cases}>
        {calm ? (
          <span className="text-success-700">All within their deadline</span>
        ) : (
          <>
            <span className={sla.overdue > 0 ? 'font-medium text-error-700' : undefined}>{sla.overdue} overdue</span>
            {' · '}
            <span className={sla.due_within_24h > 0 ? 'font-medium text-warning-800' : undefined}>{sla.due_within_24h} due in 24 h</span>
          </>
        )}
      </Figure>
      <Figure label="Auto-resolved" value={formatPercent(m.auto_resolve_rate)} to={`${paths.cases}?queue=auto_resolved`}>
        of {m.cases.total} complaints, no person needed
      </Figure>
      <Figure label="Override rate" value={formatPercent(human.override_rate)} to={`${paths.cases}?queue=approved&changed=1`}>
        {decided === 0 ? 'No human decisions yet' : `People changed the agent on ${human.rejected + human.edited_and_approved} of ${decided}`}
      </Figure>
      <Figure label="Refunds awaiting approval" value={formatMoney(refunds.awaiting)} to={paths.cases}>
        In open approval cases (simulated)
      </Figure>
    </section>
  )
}

/** A headline number that opens the cases behind it. */
function Figure({ label, value, to, children }: { label: string; value: ReactNode; to: string; children: ReactNode }) {
  return (
    <Link to={to} className="block p-card transition-colors hover:bg-subtle sm:px-5 sm:py-4">
      <p className="text-xs font-medium text-secondary">{label}</p>
      <p className="mt-1 font-display text-4xl font-semibold text-primary tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-secondary">{children}</p>
    </Link>
  )
}
