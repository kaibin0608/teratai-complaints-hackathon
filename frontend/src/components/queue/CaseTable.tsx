import { Flag, LoaderCircle, PenLine, TriangleAlert } from 'lucide-react'
import { Link, useNavigate } from 'react-router'
import { Badge } from '@/components/shared/Badge'
import { CategoryTag } from '@/components/shared/CategoryTag'
import { HoldBadge } from '@/components/shared/HoldBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { SelfCheckBadge } from '@/components/shared/SelfCheckBadge'
import { SLATimer } from '@/components/shared/SLATimer'
import { VulnerableBadge } from '@/components/shared/VulnerableBadge'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { actionLabel } from '@/lib/events'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { holdReasonLabel, outcomeLabel } from '@/lib/labels'
import { paths } from '@/lib/paths'
import type { CaseListItem } from '@/lib/types'
import { useNameOf } from '@/hooks/useNameOf'

const COLUMNS = ['Priority', 'Case', 'Customer', 'Category', 'Decision', 'Status', 'Resolve SLA'] as const

export function CaseTable({ items }: { items: readonly CaseListItem[] }) {
  return (
    <div className="overflow-x-auto rounded-card border border-default">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-[11px] tracking-wide text-secondary uppercase">
          <tr>
            {COLUMNS.map((label) => (
              <th key={label} scope="col" className="px-cell-x py-cell-y font-medium whitespace-nowrap">
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
    <tr onClick={() => navigate(paths.case(item.complaint_id))} className="cursor-pointer align-top transition-colors focus-within:bg-subtle hover:bg-subtle">
      <td className="px-cell-x py-cell-y">{item.priority && <PriorityBadge priority={item.priority} />}</td>
      <td className="px-cell-x py-cell-y whitespace-nowrap">
        <Link to={paths.case(item.complaint_id)} className="font-medium text-primary hover:text-link">
          {item.complaint_id}
        </Link>
        <div className="text-xs text-secondary tabular-nums">{formatIsoTime(item.received_at)}</div>
      </td>
      <td className="px-cell-x py-cell-y">
        <div className="font-medium text-primary">{item.customer_name ?? <span className="font-normal text-secondary">Unknown customer</span>}</div>
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
        <td colSpan={4} className="px-cell-x py-cell-y text-secondary">
          <span className="inline-flex items-center gap-2">
            <LoaderCircle size={14} aria-hidden className="animate-spin" />
            Agent is working on it
          </span>
        </td>
      ) : item.status === 'error' ? (
        <td colSpan={4} className="px-cell-x py-cell-y">
          <Badge tone="error" icon={TriangleAlert}>
            The agent could not finish this case
          </Badge>
        </td>
      ) : (
        <>
          <td className="px-cell-x py-cell-y">{item.category && <CategoryTag category={item.category} />}</td>
          <td className="px-cell-x py-cell-y whitespace-nowrap">
            {item.outcome ? (
              <>
                <div className="text-primary">{outcomeLabel[item.outcome]}</div>
                {item.outcome === 'REFUND' && item.refund_amount_myr && (
                  <div className="text-xs font-medium text-body tabular-nums">{formatMoney(item.refund_amount_myr)}</div>
                )}
              </>
            ) : (
              <span className="text-secondary">—</span>
            )}
          </td>
          <td className="px-cell-x py-cell-y">
            <StatusCell item={item} />
          </td>
          <td className="px-cell-x py-cell-y whitespace-nowrap">
            {open && item.resolve_due_at ? (
              <SLATimer start={item.received_at} due={item.resolve_due_at} plain />
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
  const nameOf = useNameOf()
  const holdIsTheReason = item.hold_reason !== null && item.waiting_reason === holdReasonLabel[item.hold_reason]
  return (
    <div className="flex flex-col items-start gap-1">
      {item.waiting_reason && !holdIsTheReason && <span className="text-body">{item.waiting_reason}</span>}
      {!item.waiting_reason && <QueueBadge queue={item.queue} />}
      {/* Who closed it, or that the holding reply has already gone to a fraud customer. */}
      {item.human_action && (
        <span className="text-xs text-secondary">
          {actionLabel(item.human_action.action)} · {nameOf(item.human_action.actor)}
        </span>
      )}
      {item.queue === 'with_fraud_team' && item.sent && !item.human_action && <span className="text-xs text-secondary">Holding reply sent</span>}
      {item.overridden && (
        <Badge tone="warning" icon={PenLine} title="People changed the agent's decision or reply">
          Changed by people
        </Badge>
      )}
      {item.self_check === 'flagged' && <SelfCheckBadge result="flagged" />}
      {(item.workflow || item.hold_reason) && (
        <div className="flex flex-wrap gap-1">
          {item.workflow && <WorkflowBadge workflow={item.workflow} />}
          {item.hold_reason && <HoldBadge reason={item.hold_reason} />}
        </div>
      )}
      {item.escalation && item.workflow === 'escalated' && (
        <span className="text-xs text-secondary">
          {nameOf(item.escalation.by)}: {item.escalation.reason}
        </span>
      )}
      {item.assigned_to && <span className="text-xs text-secondary">Assigned to {nameOf(item.assigned_to)}</span>}
    </div>
  )
}
