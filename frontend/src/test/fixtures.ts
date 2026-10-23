import type { CaseDetail, Escalation, Queue, TxnRow, User, Workflow } from '@/lib/types'

export const officer: User = { username: 'officer1', full_name: 'Aina Rahman', role: 'officer', approval_limit_myr: '2000.00' }
export const fraudAnalyst: User = { username: 'fraud1', full_name: 'Farid Hassan', role: 'fraud', approval_limit_myr: '5000.00' }
export const manager: User = { username: 'manager1', full_name: 'Mei Ling Tan', role: 'manager', approval_limit_myr: null }

export interface CaseOptions {
  queue?: Queue
  workflow?: Workflow | null
  sensitive?: boolean
  assignedTo?: string | null
  /** The refund (officer's limit basis). */
  refund?: string
  /** The matched transaction amount (fraud analyst's limit basis). */
  disputed?: string
  sent?: boolean
  /** The agent's reply passes the self-check. */
  replyPassed?: boolean
  /** An edited draft waiting for approval, and its self-check result. */
  draft?: 'passed' | 'flagged' | null
  proposal?: Escalation['proposal']
}

/** A minimal case detail: an approval case by default. Override only what a test is about. */
export function makeCase(o: CaseOptions = {}): CaseDetail {
  const queue = o.queue ?? 'awaiting_approval'
  const fraud = queue === 'with_fraud_team'
  const workflow = o.workflow ?? null
  const txn = { txn_id: 'TXN-0000001', amount_myr: o.disputed ?? '100.00', time: '2026-09-01T10:00:00' } as TxnRow
  return {
    case: {
      complaint_id: 'CMP-00001',
      status: 'done',
      queue,
      case_state: queue as never,
      sent: o.sent ?? false,
      error: null,
      waiting_reason: null,
      human_action: null,
      autonomous_run_id: 'run-1',
      current_run_id: 'run-1',
      created_at: '2026-09-01T10:00:00',
      updated_at: '2026-09-01T10:00:00',
      workflow,
      sensitive: o.sensitive ?? false,
      sensitive_reason: o.sensitive ? 'Customer aged 65+' : null,
      assigned_to: o.assignedTo ?? null,
      escalation:
        workflow === 'escalated'
          ? { by: 'officer1', at: '2026-09-02T09:00:00', reason: 'over limit', proposal: o.proposal ?? { action: 'approve', reply_text: 'x', edited: false, self_check: 'passed' } }
          : null,
    },
    complaint: { customer_id: 'CUS-00001', received_at: '2026-09-01T10:00:00', channel: 'App chat', subject: '', text: 'text' },
    customer: null,
    clues: null,
    match: null,
    decision: {
      category: fraud ? 'SCAM_TRANSFER' : 'ATM_NOT_DISPENSED',
      matched_txn_id: txn.txn_id,
      outcome: fraud ? 'INVESTIGATE' : 'REFUND',
      refund_amount_myr: fraud ? '0.00' : (o.refund ?? '100.00'),
      priority: 'P2',
      reply_language: 'EN',
      route: fraud ? 'FRAUD_TEAM' : 'HUMAN_APPROVAL',
      policy_route: fraud ? 'FRAUD_TEAM' : 'HUMAN_APPROVAL',
      rule_id: 'TEST.RULE',
      calculation: { explanation: '', inputs: {} },
      hold_reason: null,
      vulnerable: o.sensitive ?? false,
      ack_due_at: '2026-09-02T10:00:00',
      resolve_due_at: '2026-09-10T10:00:00',
    },
    evidence: { matched_txn: txn, related_txns: [], reversal: null, atm_journal: null, fee_schedule_row: null, allowed_txn_ids: [txn.txn_id], allowed_amounts: [] },
    other_issues: [],
    reply: {
      text: 'reply',
      redraft_count: 0,
      self_check: { passed: o.replyPassed ?? true, problems: [], found_txn_ids: [], found_amounts: [] },
    },
    usage: null,
    runs: [],
    events: [],
    outbound: [],
    draft_reply: o.draft ? { text: 'edited', self_check: o.draft, problems: [], by: 'officer1', at: '2026-09-01T11:00:00' } : null,
    fraud_outcome: null,
    autonomous: null,
    final: null,
    differs: { decision: false, refund: false, reply: false },
  }
}
