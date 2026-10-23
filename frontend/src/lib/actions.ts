/**
 * Which buttons a user gets on a case, and why. Pure rules from docs/UI_API.md ("The rules your
 * screens should show") and PLAN.md Roles; the backend enforces every one of them again.
 */
import { isOpen } from './case'
import { compareMoney } from './money'
import type { CaseAction, CaseDetail, Money, User } from './types'
import type { NameOf } from './people'

/** Platform actions the case page offers. */
export type ActionKey = CaseAction

export interface PlannedAction {
  key: ActionKey
  emphasis: 'primary' | 'secondary' | 'danger' | 'ghost'
  /** Why the button is locked; shown as its tooltip. */
  disabledReason?: string
}

/** Approval headroom: the amount the limit applies to, against the user's limit. */
export interface LimitInfo {
  /** "this refund" (officer) or "the disputed transaction" (fraud analyst). */
  subject: string
  amount: Money
  limit: Money
  over: boolean
}

export interface ActionPlan {
  /** Left to right; the last primary one is the main action. */
  actions: PlannedAction[]
  /** Why there are no (or fewer) buttons. */
  notice: string | null
  limit: LimitInfo | null
}

const NONE: ActionPlan = { actions: [], notice: null, limit: null }
const only = (notice: string): ActionPlan => ({ ...NONE, notice })

export function planActions(detail: CaseDetail, user: User, nameOf: NameOf = (username) => username): ActionPlan {
  const plan = planFor(detail, user, nameOf)
  // The manager can hand any open case to someone else (once assigned, only that person or the manager can act).
  if (user.role !== 'manager' || plan.actions.length === 0) return plan
  return { ...plan, actions: [{ key: 'reassign', emphasis: 'ghost' }, ...plan.actions] }
}

function planFor(detail: CaseDetail, user: User, nameOf: NameOf): ActionPlan {
  const { case: c } = detail
  if (!isOpen(detail)) return NONE
  if (c.workflow === 'reprocessing') return only('The agent is re-running this case. Actions unlock when it finishes.')
  if (c.workflow === 'escalated') return planEscalated(detail, user)
  if (c.assigned_to && c.assigned_to !== user.username && user.role !== 'manager') {
    return only(`Assigned to ${nameOf(c.assigned_to)}: only they or the manager can act on it.`)
  }
  if (c.queue === 'awaiting_approval') return planApproval(detail, user)
  if (c.queue === 'with_fraud_team') return planFraud(detail, user)
  return NONE
}

function planEscalated(detail: CaseDetail, user: User): ActionPlan {
  if (user.role !== 'manager') return only('Escalated to the manager: waiting for their decision.')
  const canEdit = detail.case.escalation?.proposal.action === 'approve'
  return {
    ...NONE,
    actions: [
      { key: 'second-tier-reject', emphasis: 'danger' },
      ...(canEdit ? [{ key: 'edit-reply', emphasis: 'secondary' } as const] : []),
      { key: 'second-tier-approve', emphasis: 'primary' },
    ],
  }
}

/** An edit waiting for approval, or else the agent's reply, failed the self-check. */
function replyFlagged(detail: CaseDetail): boolean {
  if (detail.draft_reply) return detail.draft_reply.self_check === 'flagged'
  return detail.reply?.self_check ? !detail.reply.self_check.passed : false
}

function planApproval(detail: CaseDetail, user: User): ActionPlan {
  if (user.role === 'fraud') return NONE
  const { case: c, decision } = detail
  const refund = decision?.refund_amount_myr ?? '0.00'
  const officer = user.role === 'officer'
  const limit: LimitInfo | null =
    officer && user.approval_limit_myr
      ? { subject: 'this refund', amount: refund, limit: user.approval_limit_myr, over: compareMoney(refund, user.approval_limit_myr) > 0 }
      : null
  const mustEscalate = officer && (limit?.over === true || c.sensitive)

  const actions: PlannedAction[] = [
    { key: 'reject', emphasis: 'danger' },
    { key: 'send-back', emphasis: 'secondary' },
    ...(c.sensitive ? [] : [{ key: 'flag-sensitive', emphasis: 'ghost' } as const]),
    ...(officer ? [{ key: 'escalate', emphasis: mustEscalate ? 'primary' : 'secondary' } as const] : []),
    { key: 'edit-reply', emphasis: 'secondary' },
  ]
  if (!mustEscalate) {
    actions.push({
      key: 'approve',
      emphasis: 'primary',
      disabledReason: replyFlagged(detail) ? 'The reply fails the self-check. Edit it first.' : undefined,
    })
  }
  const notice = mustEscalate
    ? limit?.over
      ? 'This refund is over your limit: escalate it to the manager.'
      : 'Sensitive case: escalate it to the manager.'
    : null
  return { actions, notice, limit }
}

function planFraud(detail: CaseDetail, user: User): ActionPlan {
  if (user.role === 'officer') return NONE
  const { case: c, evidence } = detail
  const analyst = user.role === 'fraud'
  const disputed = evidence?.matched_txn?.amount_myr ?? null
  const limit: LimitInfo | null =
    analyst && user.approval_limit_myr && disputed
      ? { subject: 'the disputed transaction', amount: disputed, limit: user.approval_limit_myr, over: compareMoney(disputed, user.approval_limit_myr) > 0 }
      : null

  if (c.workflow === null && !c.sent) {
    return { ...NONE, actions: [{ key: 'acknowledge', emphasis: 'primary' }], notice: 'Acknowledging sends the customer the holding reply.' }
  }
  if (c.workflow !== 'investigating') return NONE

  const mustEscalate = analyst && (limit?.over === true || c.sensitive)
  const actions: PlannedAction[] = [
    { key: 'investigate', emphasis: 'secondary' },
    ...(c.sensitive ? [] : [{ key: 'flag-sensitive', emphasis: 'ghost' } as const]),
    ...(analyst ? [{ key: 'escalate', emphasis: mustEscalate ? 'primary' : 'secondary' } as const] : []),
  ]
  if (!mustEscalate) actions.push({ key: 'record-outcome', emphasis: 'primary' })
  const notice = mustEscalate
    ? limit?.over
      ? 'The disputed transaction is over your limit: escalate it to the manager.'
      : 'Sensitive case: escalate it to the manager.'
    : null
  return { actions, notice, limit }
}
