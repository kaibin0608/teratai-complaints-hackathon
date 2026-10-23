import { Flag, LoaderCircle, PenLine, TriangleAlert } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { Badge } from '@/components/shared/Badge'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { HoldBadge } from '@/components/shared/HoldBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { SelfCheckBadge } from '@/components/shared/SelfCheckBadge'
import { SLATimer } from '@/components/shared/SLATimer'
import { VulnerableBadge } from '@/components/shared/VulnerableBadge'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { cx } from '@/lib/cx'
import { actionLabel } from '@/lib/events'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { holdReasonLabel, outcomeLabel } from '@/lib/labels'
import { paths } from '@/lib/paths'
import type { CaseListItem } from '@/lib/types'

/*
 * Below 1360 px the Self-check column is dropped; a flagged reply still shows in the Status cell.
 * Tailwind only generates classes it can read literally, so these are written out in full.
 */
const WIDE_ONLY_CELL = 'hidden min-[1360px]:table-cell'
const NARROW_ONLY = 'min-[1360px]:hidden'

const COLUMNS: readonly { label: string; wideOnly?: boolean }[] = [
  { label: 'Priority' },
  { label: 'Case' },
  { label: 'Customer' },
  { label: 'Category' },
  { label: 'Decision' },
  { label: 'Status' },
  { label: 'Self-check', wideOnly: true },
  { label: 'Resolve SLA' },
]

export function CaseTable({ items }: { items: readonly CaseListItem[] }) {
  return (
    <div className="overflow-x-auto rounded-card border border-default">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-xs text-secondary">
          <tr>
            {COLUMNS.map(({ label, wideOnly }) => (
              <th
                key={label}
                scope="col"
                className={cx('px-cell-x py-cell-y font-medium whitespace-nowrap', wideOnly && WIDE_ONLY_CELL)}
              >
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {items.map((item) => (
            <CaseRow key={item.complaint_id} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CaseRow({ item }: { item: CaseListItem }) {
  const navigate = useNavigate()
  const open = (item.queue === 'awaiting_approval' || item.queue === 'with_fraud_team') && item.workflow !== 'closed'
  return (
    <tr onClick={() => navigate(paths.case(item.complaint_id))} className="cursor-pointer align-top hover:bg-subtle">
      <td className="px-cell-x py-cell-y">{item.priority && <PriorityBadge priority={item.priority} />}</td>
      <td className="px-cell-x py-cell-y whitespace-nowrap">
        <Link to={paths.case(item.complaint_id)} className="font-medium text-primary hover:text-link">
          {item.complaint_id}
        </Link>
        <div className="text-xs text-secondary tabular-nums">{formatIsoTime(item.received_at)}</div>
      </td>
      <td className="px-cell-x py-cell-y">
        <div className="text-primary">{item.customer_name ?? <span className="text-secondary">Unknown customer</span>}</div>
        <div className="mt-0.5 flex flex-wrap items-center gap-1 text-xs text-secondary">
          {item.channel}
          {item.vulnerable && <VulnerableBadge />}
          {/* 65+ is already the vulnerable badge; this is a case someone flagged by hand. */}
          {item.sensitive && !item.vulnerable && (
            <Badge tone="aubergine" icon={Flag} title={item.sensitive_reason ?? 'Flagged sensitive'}>
              Sensitive
            </Badge>
          )}
        </div>
        {item.subject && <div className="mt-0.5 max-w-[16rem] truncate text-xs text-secondary italic">{item.subject}</div>}
      </td>

      {item.status === 'processing' ? (
        <td colSpan={5} className="px-cell-x py-cell-y text-secondary">
          <span className="inline-flex items-center gap-2">
            <LoaderCircle size={14} aria-hidden className="animate-spin" />
            Agent is working on it
          </span>
        </td>
      ) : item.status === 'error' ? (
        <td colSpan={5} className="px-cell-x py-cell-y">
          <Badge tone="error" icon={TriangleAlert}>
            The agent could not finish this case
          </Badge>
        </td>
      ) : (
        <>
          <td className="px-cell-x py-cell-y">{item.category && <CategoryBadge category={item.category} />}</td>
          <td className="px-cell-x py-cell-y whitespace-nowrap">
            {item.outcome ? (
              <>
                <div className="text-primary">{outcomeLabel[item.outcome]}</div>
                {item.outcome === 'REFUND' && item.refund_amount_myr && (
                  <div className="text-xs text-secondary tabular-nums">{formatMoney(item.refund_amount_myr)}</div>
                )}
              </>
            ) : (
              <span className="text-secondary">—</span>
            )}
          </td>
          <td className="px-cell-x py-cell-y">
            <StatusCell item={item} />
          </td>
          <td className={cx('px-cell-x py-cell-y', WIDE_ONLY_CELL)}>
            {item.self_check && <SelfCheckBadge result={item.self_check} compact />}
          </td>
          <td className="px-cell-x py-cell-y whitespace-nowrap">
            {open && item.resolve_due_at ? (
              <SLATimer start={item.received_at} due={item.resolve_due_at} />
            ) : (
              <span className="text-secondary">—</span>
            )}
          </td>
        </>
      )}
    </tr>
  )
}

/** Why it's waiting (the backend's text), or where it ended up; a hold shows once, as its badge. */
function StatusCell({ item }: { item: CaseListItem }) {
  const holdIsTheReason = item.hold_reason !== null && item.waiting_reason === holdReasonLabel[item.hold_reason]
  return (
    <div className="flex flex-col items-start gap-1">
      {item.waiting_reason && !holdIsTheReason && <span className="text-body">{item.waiting_reason}</span>}
      {!item.waiting_reason && <QueueBadge queue={item.queue} />}
      {/* Who closed it, or that the holding reply has already gone to a fraud customer. */}
      {item.human_action && (
        <span className="text-xs text-secondary">
          {actionLabel(item.human_action.action)} · {item.human_action.actor}
        </span>
      )}
      {item.queue === 'with_fraud_team' && item.sent && <span className="text-xs text-secondary">Holding reply sent</span>}
      {item.overridden && (
        <Badge tone="warning" icon={PenLine} title="People changed the agent's decision or reply">
          Changed by people
        </Badge>
      )}
      {item.self_check === 'flagged' && (
        <div className={NARROW_ONLY}>
          <SelfCheckBadge result="flagged" />
        </div>
      )}
      {(item.workflow || item.hold_reason) && (
        <div className="flex flex-wrap gap-1">
          {item.workflow && <WorkflowBadge workflow={item.workflow} />}
          {item.hold_reason && <HoldBadge reason={item.hold_reason} />}
        </div>
      )}
      {item.escalation && item.workflow === 'escalated' && (
        <span className="text-xs text-secondary">
          {item.escalation.by}: {item.escalation.reason}
        </span>
      )}
      {item.assigned_to && <span className="text-xs text-secondary">Assigned to {item.assigned_to}</span>}
    </div>
  )
}
