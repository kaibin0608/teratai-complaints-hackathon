import type {
  Category,
  FraudOutcome,
  HoldReason,
  MatchStatus,
  Outcome,
  Queue,
  Role,
  Route,
  Workflow,
} from './types'

/** Human-readable labels for backend enum values. */

export const roleLabel: Record<Role, string> = {
  officer: 'Complaints Officer',
  fraud: 'Fraud Analyst',
  manager: 'Manager',
}

export const categoryLabel: Record<Category, string> = {
  DUPLICATE_CHARGE: 'Duplicate charge',
  FAILED_TRANSFER: 'Failed transfer',
  ATM_NOT_DISPENSED: 'ATM not dispensed',
  UNAUTHORISED_CARD: 'Unauthorised card',
  SCAM_TRANSFER: 'Scam transfer',
  FEE_DISPUTE: 'Fee dispute',
  SERVICE_QUALITY: 'Service quality',
}

export const outcomeLabel: Record<Outcome, string> = {
  REFUND: 'Refund',
  DECLINE: 'Decline',
  INVESTIGATE: 'Investigate',
  INFO_ONLY: 'Info only',
}

export const routeLabel: Record<Route, string> = {
  AUTO_RESOLVE: 'Auto-resolve',
  HUMAN_APPROVAL: 'Officer approval',
  FRAUD_TEAM: 'Fraud team',
}

/** Queue tabs (UI_API.md "Which endpoint feeds which screen"). */
export const queueLabel: Record<Queue, string> = {
  processing: 'Processing',
  error: 'Error',
  auto_resolved: 'Auto-resolved',
  awaiting_approval: 'Awaiting approval',
  with_fraud_team: 'Fraud team',
  approved: 'Approved',
  rejected: 'Rejected',
}

export const workflowLabel: Record<Workflow, string> = {
  escalated: 'Escalated',
  reprocessing: 'Re-running',
  investigating: 'Investigating',
  closed: 'Closed',
}

/** Also the queue's "why it's waiting" text for held cases (USERFLOW.md §2). */
export const holdReasonLabel: Record<HoldReason, string> = {
  customer_not_found: 'Unknown customer',
  ambiguous_match: 'Ambiguous match',
  no_match: 'No matching transaction',
  category_revised: 'Category revised',
  self_check_failed: 'Self-check failed',
  unknown_auth_method: 'Unknown auth method',
  llm_error: 'LLM error',
}

/** What a held case means for the reviewer. */
export const holdReasonHelp: Record<HoldReason, string> = {
  customer_not_found: 'The customer ID is not in our records, so no transaction lookup was done.',
  ambiguous_match: 'Several transactions fit the complaint equally well. Confirm the matched transaction before acting.',
  no_match: 'No transaction in the 45-day window fits the complaint. Check the complaint details.',
  category_revised: 'No transaction fit the first category, so the agent tried a related one. Confirm the category.',
  self_check_failed: 'The drafted reply mentions an ID or amount that is not in the evidence. Edit the reply before sending.',
  unknown_auth_method: 'The card payment used an authentication method the policy does not cover. Never refund automatically.',
  llm_error: 'The language model failed on this complaint. Handle it manually.',
}

export const matchStatusLabel: Record<MatchStatus, string> = {
  confident: 'Confident match',
  ambiguous: 'Ambiguous match',
  none: 'No match',
  not_applicable: 'No transaction involved',
}

export const fraudOutcomeLabel: Record<FraudOutcome, string> = {
  confirmed_fraud: 'Confirmed fraud',
  not_fraud: 'Not fraud',
  recall_succeeded: 'Recall succeeded',
  recall_failed: 'Recall failed',
}
