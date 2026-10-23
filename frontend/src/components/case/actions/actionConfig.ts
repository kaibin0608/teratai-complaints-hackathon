import {
  ArrowUpRight,
  BadgeCheck,
  Ban,
  CircleCheck,
  FilePen,
  Flag,
  ListChecks,
  Send,
  ShieldCheck,
  Undo2,
  UserRoundCog,
  type LucideIcon,
} from 'lucide-react'
import { formatMoney } from '@/lib/format'
import { fraudOutcomeLabel } from '@/lib/labels'
import type { ActionKey } from '@/lib/actions'
import { FRAUD_OUTCOMES, type CaseDetail } from '@/lib/types'
import type { NameOf } from '@/lib/people'

/** Form fields are named after the request body keys (ActionBodies in lib/types.ts). */
export interface FieldSpec {
  name: 'reason' | 'note' | 'reply_text' | 'outcome' | 'kind' | 'username'
  label: string
  /** `user` is a person picker loaded from GET /api/users. */
  input: 'text' | 'textarea' | 'select' | 'user'
  required: boolean
  hint?: string
  options?: readonly { value: string; label: string }[]
  rows?: number
  defaultValue?: string
}

export interface ActionSpec {
  label: string
  icon: LucideIcon
  title: string
  /** What will happen, in plain words, shown above the form. */
  description: (detail: CaseDetail, nameOf: NameOf) => string | null
  submit: string
  fields: (detail: CaseDetail) => FieldSpec[]
}

const reason = (label = 'Reason', required = true, hint?: string): FieldSpec => ({ name: 'reason', label, input: 'text', required, hint })
const outcomeOptions = FRAUD_OUTCOMES.map((value) => ({ value, label: fraudOutcomeLabel[value] }))

const isFraudCase = (detail: CaseDetail) => detail.case.queue === 'with_fraud_team'
const language = (detail: CaseDetail) => (detail.decision?.reply_language === 'MS' ? 'Malay' : 'English')
const refund = (detail: CaseDetail) => formatMoney(detail.decision?.refund_amount_myr ?? '0.00')

export const ACTIONS: Record<ActionKey, ActionSpec> = {
  approve: {
    label: 'Approve',
    icon: CircleCheck,
    title: 'Approve and send',
    description: (d) => {
      const edited = d.draft_reply ? ' (your edited draft)' : ''
      const money = d.decision?.outcome === 'REFUND' ? ` and the refund of ${refund(d)}` : ''
      return `Sends the ${language(d)} reply${edited}${money} to the customer. Simulated: nothing really leaves the system.`
    },
    submit: 'Approve and send',
    fields: () => [reason('Note', false)],
  },
  reject: {
    label: 'Reject',
    icon: Ban,
    title: 'Reject the agent’s decision',
    description: () => 'Nothing is sent to the customer. You then handle the case yourself.',
    submit: 'Reject',
    fields: () => [reason('Reason', true, 'Recorded in the audit log.')],
  },
  'edit-reply': {
    label: 'Edit reply',
    icon: FilePen,
    title: 'Edit the reply',
    description: () =>
      'The self-check runs on your text. A reply that mentions a transaction ID or amount that is not in the evidence cannot be approved.',
    submit: 'Save edit',
    fields: (d) => [
      { name: 'reply_text', label: 'Reply', input: 'textarea', required: true, rows: 9, defaultValue: d.draft_reply?.text ?? d.reply?.text ?? '' },
      reason('What did you change?'),
    ],
  },
  'send-back': {
    label: 'Send back',
    icon: Undo2,
    title: 'Send back to the agent',
    description: () => 'The agent re-runs with your note added to the complaint. The case waits for a person afterwards; it never goes out on its own.',
    submit: 'Send back',
    fields: () => [{ name: 'note', label: 'Note for the agent', input: 'textarea', required: true, rows: 3, hint: 'e.g. “It is the RM1,383.20 charge on 12 Sep.”' }],
  },
  escalate: {
    label: 'Escalate to manager',
    icon: ArrowUpRight,
    title: 'Escalate to the manager',
    description: (d) =>
      isFraudCase(d)
        ? 'The manager decides. Propose the outcome you would record: it is applied if they approve.'
        : 'The manager decides. Your reply (or edited draft) is the proposal they approve or reject. Nothing is sent until then.',
    submit: 'Escalate',
    fields: (d) => [
      reason('Why are you escalating?'),
      ...(isFraudCase(d) ? [{ name: 'outcome', label: 'Proposed outcome', input: 'select', required: true, options: outcomeOptions } satisfies FieldSpec] : []),
    ],
  },
  'flag-sensitive': {
    label: 'Flag sensitive',
    icon: Flag,
    title: 'Flag as sensitive',
    description: () => 'A sensitive case needs the manager’s decision whatever the amount.',
    submit: 'Flag sensitive',
    fields: () => [reason('Why is it sensitive?')],
  },
  'second-tier-approve': {
    label: 'Approve (manager)',
    icon: BadgeCheck,
    title: 'Approve as manager',
    description: (d) =>
      d.case.escalation?.proposal.action === 'record_outcome'
        ? `Records the proposed outcome (${fraudOutcomeLabel[d.case.escalation.proposal.outcome]}) and closes the case.`
        : `Sends the proposed reply${d.decision?.outcome === 'REFUND' ? ` and the refund of ${refund(d)}` : ''} to the customer. Simulated.`,
    submit: 'Approve',
    fields: () => [reason()],
  },
  'second-tier-reject': {
    label: 'Reject (manager)',
    icon: Ban,
    title: 'Reject as manager',
    description: (d) =>
      isFraudCase(d) ? 'The case goes back to the analyst to keep investigating.' : 'Nothing is sent to the customer, and the case closes as rejected.',
    submit: 'Reject',
    fields: () => [reason()],
  },
  reassign: {
    label: 'Reassign',
    icon: UserRoundCog,
    title: 'Reassign the case',
    description: (d, nameOf) =>
      `Hands the case to another person. Only they, or you, can then act on it.${d.case.assigned_to ? ` Currently assigned to ${nameOf(d.case.assigned_to)}.` : ''}`,
    submit: 'Reassign',
    fields: () => [{ name: 'username', label: 'Assign to', input: 'user', required: true }, reason('Note', false)],
  },
  acknowledge: {
    label: 'Acknowledge',
    icon: Send,
    title: 'Acknowledge the case',
    description: (d) => `Sends the customer the ${language(d)} holding reply (simulated) and starts the investigation. No decision and no money yet.`,
    submit: 'Acknowledge',
    fields: () => [reason('Note', false)],
  },
  investigate: {
    label: 'Log investigation',
    icon: ListChecks,
    title: 'Log an investigation step',
    description: () => 'Adds an entry to the case timeline. You can log as many as you need.',
    submit: 'Log entry',
    fields: () => [
      {
        name: 'kind',
        label: 'Kind',
        input: 'select',
        required: true,
        options: [
          { value: 'investigation', label: 'Investigation' },
          { value: 'recall_attempt', label: 'Recall attempt' },
        ],
      },
      { name: 'note', label: 'What was done', input: 'textarea', required: true, rows: 3 },
    ],
  },
  'record-outcome': {
    label: 'Record outcome',
    icon: ShieldCheck,
    title: 'Record the fraud outcome',
    description: () => 'Closes the case. No further message goes to the customer.',
    submit: 'Record outcome',
    fields: () => [{ name: 'outcome', label: 'Outcome', input: 'select', required: true, options: outcomeOptions }, reason()],
  },
}
