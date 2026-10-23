import { Badge, type BadgeTone } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { categoryLabel, matchStatusLabel } from '@/lib/labels'
import type { CaseDetail, MatchStatus } from '@/lib/types'

const statusTone: Record<MatchStatus, BadgeTone> = {
  confident: 'success',
  ambiguous: 'warning',
  none: 'error',
  not_applicable: 'neutral',
}

/** Every transaction the agent considered, best first. Open by default when the match needs checking. */
export function MatchCard({ detail }: { detail: CaseDetail }) {
  const { match } = detail
  if (!match || match.status === 'not_applicable') return null
  const needsCheck = match.status !== 'confident'

  return (
    <Card title="Transaction match" aside={<Badge tone={statusTone[match.status]}>{matchStatusLabel[match.status]}</Badge>}>
      {match.category_revised && (
        <p className="mb-3 text-sm text-warning-800">
          No transaction fitted the first category, so the agent revised it to {categoryLabel[match.category]}.
        </p>
      )}
      {match.candidates.length === 0 ? (
        <p className="text-sm text-secondary">No candidate transactions in the 45-day window.</p>
      ) : (
        <details open={needsCheck}>
          <summary className="cursor-pointer text-sm font-medium text-link select-none hover:text-link-hover">
            {match.candidates.length} candidate{match.candidates.length === 1 ? '' : 's'} considered
          </summary>
          <ol className="mt-2 divide-y divide-neutral-100 rounded-control border border-subtle">
            {match.candidates.map((candidate, index) => (
              <li key={candidate.txn_id} className="flex items-start gap-3 px-3 py-2 text-sm">
                <span className="w-10 shrink-0 text-right font-medium text-primary tabular-nums">
                  {Math.round(candidate.score * 100)}%
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-primary tabular-nums">
                    {candidate.txn_id}
                    {index === 0 && match.txn_id === candidate.txn_id && <Badge tone="brand">Chosen</Badge>}
                  </div>
                  <div className="text-xs text-secondary">{candidate.reasons.join(' · ')}</div>
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}
    </Card>
  )
}
