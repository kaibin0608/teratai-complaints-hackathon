/**
 * The toast for each platform action: what happened, to which case, and what follows. Pure, so the wording is tested.
 * Weights: a toast says an action worked; a failed action stays in its dialog (so a typed reason is not lost);
 * saving an edited reply is shown inline in the dialog (its self-check result), so it has no toast.
 */
import type { ToastInput } from '@/context/toast-context'
import type { ActionKey } from './actions'
import { formatMoney } from './format'
import { fraudOutcomeLabel } from './labels'
import type { NameOf } from './people'
import type { ActionBodies, CaseDetail, FraudOutcome } from './types'

/** Where the person was taken after an advancing action: the next case that needs them, or back to their queue. */
export type Advanced = 'next-case' | 'queue'

const isFraudCase = (detail: CaseDetail) => detail.case.queue === 'with_fraud_team'

export function actionToast(
  action: ActionKey,
  detail: CaseDetail,
  body: Partial<ActionBodies[ActionKey]>,
  nameOf: NameOf,
): ToastInput | null {
  const id = detail.case.complaint_id
  const field = (name: string): string | undefined => {
    const value = (body as Record<string, unknown>)[name]
    return typeof value === 'string' ? value : undefined
  }

  switch (action) {
    case 'approve': {
      const refund = detail.decision?.outcome === 'REFUND' ? detail.decision.refund_amount_myr : null
      return {
        tone: 'success',
        title: detail.draft_reply ? `Approved ${id} with your edited reply` : `Approved ${id}`,
        description: refund ? `${formatMoney(refund)} refund and reply sent to the customer (simulated).` : 'Reply sent to the customer (simulated).',
      }
    }
    case 'reject':
      return { tone: 'neutral', title: `Rejected ${id}`, description: 'Nothing was sent to the customer.' }
    case 'send-back':
      return { tone: 'info', title: `Sent ${id} back to the agent`, description: 'It runs again with your note and returns to the queue when it finishes.' }
    case 'escalate':
      return { tone: 'info', title: `Escalated ${id} to the manager`, description: 'Nothing is sent until the manager decides.' }
    case 'flag-sensitive':
      return { tone: 'warning', title: `Flagged ${id} as sensitive`, description: 'It now needs the manager’s decision.' }
    case 'edit-reply':
      return null
    case 'second-tier-approve':
      return isFraudCase(detail)
        ? { tone: 'success', title: `Approved ${id} as manager`, description: 'The analyst’s proposed outcome is recorded.' }
        : { tone: 'success', title: `Approved ${id} as manager`, description: 'The decision goes ahead and the reply is sent (simulated).' }
    case 'second-tier-reject':
      return isFraudCase(detail)
        ? { tone: 'neutral', title: `Rejected ${id} as manager`, description: 'It goes back to the analyst to keep investigating.' }
        : { tone: 'neutral', title: `Rejected ${id} as manager`, description: 'Nothing was sent to the customer, and the case is closed.' }
    case 'reassign': {
      const username = field('username')
      return { tone: 'info', title: username ? `Assigned ${id} to ${nameOf(username)}` : `Reassigned ${id}`, description: 'Only they, or a manager, can act on it now.' }
    }
    case 'acknowledge':
      return { tone: 'success', title: `Acknowledged ${id}`, description: 'Holding reply sent to the customer (simulated). The investigation has started.' }
    case 'investigate':
      return field('kind') === 'recall_attempt'
        ? { tone: 'success', title: `Recall attempt logged on ${id}` }
        : { tone: 'success', title: `Investigation note added to ${id}` }
    case 'record-outcome': {
      const outcome = field('outcome') as FraudOutcome | undefined
      return { tone: 'success', title: `Outcome recorded for ${id}`, description: outcome ? `${fraudOutcomeLabel[outcome]}.` : undefined }
    }
  }
}

/** After an advancing action the page changes, so the toast says where you are and offers the way back. */
export function withAdvance(toast: ToastInput, id: string, advanced: Advanced, caseLink: string): ToastInput {
  const where = advanced === 'next-case' ? 'Showing the next case that needs you.' : 'Nothing else is waiting for you.'
  return {
    ...toast,
    description: toast.description ? `${toast.description} ${where}` : where,
    link: { label: `Open ${id} again`, to: caseLink },
  }
}
