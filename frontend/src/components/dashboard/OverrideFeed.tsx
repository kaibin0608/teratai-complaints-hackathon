import { Link } from 'react-router'
import { Card } from '@/components/shared/Card'
import { CategoryTag } from '@/components/shared/CategoryTag'
import { useCaseList } from '@/hooks/useCaseList'
import { useNameOf } from '@/hooks/useNameOf'
import { actionLabel } from '@/lib/events'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { outcomeLabel } from '@/lib/labels'
import { paths } from '@/lib/paths'

/** Where people changed what the agent decided: the agent-versus-human gap, newest first. */
export function OverrideFeed() {
  const result = useCaseList({ overridden: true, sort: 'recent', limit: 5 })
  const nameOf = useNameOf()
  const items = result.status === 'success' ? result.data.items : []
  const total = result.status === 'success' ? result.data.total : 0

  return (
    <Card
      title="Where people changed the agent"
      aside={
        total > 5 ? (
          <Link to={`${paths.cases}?queue=approved&changed=1`} className="text-xs font-medium text-link hover:text-link-hover">
            See all {total}
          </Link>
        ) : null
      }
    >
      {result.status === 'success' && items.length === 0 ? (
        <p className="text-sm text-secondary">No one has changed an agent decision yet.</p>
      ) : (
        <ul className="-my-2 divide-y divide-neutral-100">
          {items.map((item) => (
            <li key={item.complaint_id} className="py-2.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <Link to={paths.case(item.complaint_id)} className="font-medium text-primary hover:text-link">
                  {item.complaint_id}
                </Link>
                {item.category && <CategoryTag category={item.category} />}
              </div>
              <p className="mt-0.5 text-sm text-body">
                Agent: {item.outcome ? outcomeLabel[item.outcome] : 'no decision'}
                {item.outcome === 'REFUND' && item.refund_amount_myr ? ` ${formatMoney(item.refund_amount_myr)}` : ''}
                {item.human_action && (
                  <>
                    {' → '}
                    {actionLabel(item.human_action.action)} by {nameOf(item.human_action.actor)}
                  </>
                )}
              </p>
              {item.human_action && <p className="mt-0.5 text-xs text-secondary">{formatIsoTime(item.human_action.at)}</p>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
