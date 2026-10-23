/**
 * Frontend mirror of the backend's UI contract.
 *
 * Source of truth: docs/UI_API.md (its "TypeScript types" section, copied field for field) and
 * docs/api.md. Change this file only when those change. Additions that don't alter the contract:
 * - const value lists the UI can iterate (QUEUES, CATEGORIES, …)
 * - exact row types for the raw CSV rows in `evidence` / `customer` (UI_API.md types them as records;
 *   the fields were checked against the running backend)
 *
 * Wire formats: Money is a 2-decimal string ("550.00"); Cost a 4-decimal RM string ("0.0013");
 * IsoTime is Malaysia time with no offset ("2026-07-20T22:32:00"): never convert time zones.
 */

/* ------------------------------------------------------------------ */
/* Primitives                                                          */
/* ------------------------------------------------------------------ */

export type Money = string
export type Cost = string
export type IsoTime = string
/** "YYYY-MM-DD". */
export type IsoDate = string

/* ------------------------------------------------------------------ */
/* Enumerations                                                        */
/* ------------------------------------------------------------------ */

export const QUEUES = [
  'processing',
  'error',
  'auto_resolved',
  'awaiting_approval',
  'with_fraud_team',
  'approved',
  'rejected',
] as const
export type Queue = (typeof QUEUES)[number]

/** The contract's case_state (docs/api.md): a queue other than processing/error. */
export type CaseState = Exclude<Queue, 'processing' | 'error'>

export const CASE_STATUSES = ['processing', 'done', 'error'] as const
export type CaseStatus = (typeof CASE_STATUSES)[number]

/** Bonus platform workflow on top of the queue; null when none. */
export const WORKFLOWS = ['escalated', 'reprocessing', 'investigating', 'closed'] as const
export type Workflow = (typeof WORKFLOWS)[number]

export const CATEGORIES = [
  'DUPLICATE_CHARGE',
  'FAILED_TRANSFER',
  'ATM_NOT_DISPENSED',
  'UNAUTHORISED_CARD',
  'SCAM_TRANSFER',
  'FEE_DISPUTE',
  'SERVICE_QUALITY',
] as const
export type Category = (typeof CATEGORIES)[number]

export const OUTCOMES = ['REFUND', 'DECLINE', 'INVESTIGATE', 'INFO_ONLY'] as const
export type Outcome = (typeof OUTCOMES)[number]

export const ROUTES = ['AUTO_RESOLVE', 'HUMAN_APPROVAL', 'FRAUD_TEAM'] as const
export type Route = (typeof ROUTES)[number]

export const PRIORITIES = ['P1', 'P2', 'P3'] as const
export type Priority = (typeof PRIORITIES)[number]

export const LANGUAGES = ['EN', 'MS'] as const
export type Language = (typeof LANGUAGES)[number]

export const HOLD_REASONS = [
  'customer_not_found',
  'ambiguous_match',
  'no_match',
  'category_revised',
  'self_check_failed',
  'unknown_auth_method',
  'llm_error',
] as const
export type HoldReason = (typeof HOLD_REASONS)[number]

export const MATCH_STATUSES = ['confident', 'ambiguous', 'none', 'not_applicable'] as const
export type MatchStatus = (typeof MATCH_STATUSES)[number]

export type SelfCheckResult = 'passed' | 'flagged'
export type RunKind = 'autonomous' | 'reprocess'

export const ROLES = ['officer', 'fraud', 'manager'] as const
export type Role = (typeof ROLES)[number]

export const FRAUD_OUTCOMES = ['confirmed_fraud', 'not_fraud', 'recall_succeeded', 'recall_failed'] as const
export type FraudOutcome = (typeof FRAUD_OUTCOMES)[number]

/** Complaint channels in the data (docs/data_dictionary.md). */
export const COMPLAINT_CHANNELS = ['App chat', 'Email', 'Call centre note', 'Branch form', 'Social media DM'] as const

/* ------------------------------------------------------------------ */
/* Raw CSV rows (customer, evidence): strings as in the CSVs           */
/* ------------------------------------------------------------------ */

export interface AccountRow {
  account_id: string
  customer_id: string
  product: string
  open_date: IsoDate
  status: string
  card_last4: string
}

export interface CustomerRow {
  customer_id: string
  full_name: string
  date_of_birth: IsoDate
  state: string
  city: string
  segment: string
  preferred_language: Language
  email: string
  customer_since: IsoDate
  accounts: AccountRow[]
}

/** transactions.csv row. `txn_time` is "2026-07-17 07:20:56"; `time` is the same as IsoTime; `amount` a number. */
export interface TxnRow {
  txn_id: string
  txn_time: string
  time: IsoTime
  account_id: string
  customer_id: string
  direction: 'DR' | 'CR'
  amount_myr: Money
  amount: number
  channel: string
  merchant_or_counterparty: string
  counterparty_account: string
  counterparty_bank: string
  merchant_country: string
  card_last4: string
  auth_method: string
  status: string
  description: string
}

export interface AtmJournalRow {
  txn_id: string
  atm_id: string
  atm_location: string
  requested_myr: Money
  dispensed_myr: Money
  journal_status: string
}

export interface FeeScheduleRow {
  fee_code: string
  fee_name: string
  product: string
  amount_myr: Money
  waiver_rule: string
}

/* ------------------------------------------------------------------ */
/* GET /api/cases                                                      */
/* ------------------------------------------------------------------ */

export interface HumanActionSummary {
  action: string
  actor: string
  at: IsoTime
}

export interface Escalation {
  by: string
  at: IsoTime
  reason: string
  proposal:
    | { action: 'approve'; reply_text: string; edited: boolean; self_check: SelfCheckResult }
    | { action: 'record_outcome'; outcome: FraudOutcome }
}

export interface CaseListItem {
  complaint_id: string
  customer_id: string
  /** null when the customer is unknown or the agent is still working. */
  customer_name: string | null
  received_at: IsoTime
  channel: string
  subject: string
  status: CaseStatus
  queue: Queue
  case_state: CaseState | null
  sent: boolean
  // the agent's decision (current run); null while processing or after an error
  category: Category | null
  outcome: Outcome | null
  refund_amount_myr: Money | null
  priority: Priority | null
  route: Route | null
  hold_reason: HoldReason | null
  self_check: SelfCheckResult | null
  vulnerable: boolean | null
  resolve_due_at: IsoTime | null
  /** Why the case is waiting, written by the backend; null for closed cases. */
  waiting_reason: string | null
  human_action: HumanActionSummary | null
  updated_at: IsoTime
  // bonus platform
  workflow: Workflow | null
  sensitive: boolean
  /** "Customer aged 65+" or the reason someone gave when flagging. */
  sensitive_reason: string | null
  assigned_to: string | null
  escalation: Escalation | null
  /** People changed the agent's decision or reply. */
  overridden: boolean
}

export interface CaseList {
  total: number
  limit: number
  offset: number
  /** Over all the cases you can see, ignoring filters: for tab badges. */
  counts: Record<Queue, number>
  workflow_counts: Record<Workflow, number>
  items: CaseListItem[]
}

/** GET /api/cases parameters. Enum filters take one value or a list (sent comma-separated). */
export interface CaseListQuery {
  queue?: Queue | Queue[]
  route?: Route | Route[]
  category?: Category | Category[]
  priority?: Priority | Priority[]
  /** 'none' = no hold. */
  hold_reason?: HoldReason | 'none' | (HoldReason | 'none')[]
  workflow?: Workflow | 'none' | (Workflow | 'none')[]
  sensitive?: boolean
  /** 'me' needs a token; 'none' = unassigned. */
  assigned_to?: string
  overridden?: boolean
  /** Case ID, customer ID, customer name or subject. */
  q?: string
  /** 'priority' (default): P1 first, then the earliest SLA due date. 'recent': latest activity first. */
  sort?: 'priority' | 'recent'
  /** 1–500, default 50. */
  limit?: number
  offset?: number
}

/* ------------------------------------------------------------------ */
/* GET /api/cases/{id}                                                 */
/* ------------------------------------------------------------------ */

export interface Candidate {
  txn_id: string
  /** 0..1 */
  score: number
  reasons: string[]
}

export interface LLMUsage {
  provider: string
  model: string
  tokens_in: number
  tokens_out: number
  cost_myr: Cost
  latency_ms: number
  retries: number
  cached: boolean
}

export interface AuditEvent {
  id: number
  complaint_id: string
  /** "agent" or a person's name, e.g. "Aina (officer)". */
  actor: string
  action: string
  run_id: string | null
  /** Depends on the action (UI_API.md, GET /api/audit). */
  detail: Record<string, unknown> | null
  created_at: IsoTime
}

/** What the LLM read from the text. */
export interface Clues {
  category: Category
  language: Language
  is_mixed_language: boolean
  amount_mentioned: Money | null
  other_amounts: Money[]
  amount_approximate: boolean
  counterparty_name: string | null
  counterparty_bank: string | null
  atm_location: string | null
  date_phrase: string | null
  date_exact: IsoDate | null
  card_last4: string | null
  fee_type: string | null
  fee_month: string | null
}

export interface Decision {
  category: Category
  matched_txn_id: string | null
  outcome: Outcome
  refund_amount_myr: Money
  priority: Priority
  reply_language: Language
  route: Route
  /** Route before any hold. */
  policy_route: Route
  /** e.g. "ATM.SHORTFALL_REFUND". */
  rule_id: string
  calculation: { explanation: string; inputs: Record<string, string> }
  hold_reason: HoldReason | null
  vulnerable: boolean
  ack_due_at: IsoTime | null
  resolve_due_at: IsoTime | null
}

export interface Evidence {
  matched_txn: TxnRow | null
  /** e.g. the earlier charge of a duplicate. */
  related_txns: TxnRow[]
  reversal: TxnRow | null
  atm_journal: AtmJournalRow | null
  fee_schedule_row: FeeScheduleRow | null
  /** The only IDs and amounts a reply may mention. */
  allowed_txn_ids: string[]
  allowed_amounts: Money[]
}

export interface SelfCheck {
  passed: boolean
  problems: string[]
  found_txn_ids: string[]
  found_amounts: Money[]
}

export interface CaseDetail {
  case: {
    complaint_id: string
    status: CaseStatus
    queue: Queue
    case_state: CaseState | null
    sent: boolean
    error: string | null
    waiting_reason: string | null
    human_action: { action: string; actor: string; reason: string; at: IsoTime; reply_text: string | null } | null
    autonomous_run_id: string | null
    /** Differs from autonomous_run_id after a send back. */
    current_run_id: string | null
    created_at: IsoTime
    updated_at: IsoTime
    workflow: Workflow | null
    sensitive: boolean
    sensitive_reason: string | null
    assigned_to: string | null
    escalation: Escalation | null
  }
  complaint: { customer_id: string; received_at: IsoTime; channel: string; subject: string; text: string }
  // null while processing, after an error, or (customer) when the customer is unknown
  customer: CustomerRow | null
  clues: Clues | null
  match: {
    status: MatchStatus
    txn_id: string | null
    /** The first is the chosen one. */
    candidates: Candidate[]
    category: Category
    category_revised: boolean
  } | null
  decision: Decision | null
  evidence: Evidence | null
  reply: { text: string; redraft_count: number; self_check: SelfCheck | null } | null
  usage: {
    cost_myr: Cost
    latency_ms: number
    prompt_version: string
    schema_version: string
    policy_version: string
    extract: LLMUsage
    draft: LLMUsage[]
  } | null
  runs: {
    run_id: string
    run_kind: RunKind
    created_at: IsoTime
    route: Route | null
    outcome: Outcome | null
    hold_reason: HoldReason | null
    cost_myr: Cost
    latency_ms: number
  }[]
  /** Oldest first. */
  events: AuditEvent[]
  outbound: {
    kind: 'resolution' | 'holding_reply'
    reply_text: string
    refund_amount_myr: Money
    authorised_by: string
    status: string
    created_at: IsoTime
  }[]
  // bonus platform
  /** An edit waiting to be approved. */
  draft_reply: { text: string; self_check: SelfCheckResult; problems: string[]; by: string; at: IsoTime } | null
  fraud_outcome: { outcome: FraudOutcome; by: string; at: IsoTime; reason: string; proposed_by?: string } | null
  /** The agent's own decision, never changed. */
  autonomous: {
    outcome: Outcome
    refund_amount_myr: Money
    route: Route
    matched_txn_id: string | null
    reply_text: string
  } | null
  /** What people did and what reached the customer; null until a person acts. */
  final: {
    action: string
    by: string
    at: IsoTime
    outcome: Outcome | 'REJECTED' | FraudOutcome | null
    refund_amount_myr: Money
    reply_text: string | null
    sent: boolean
  } | null
  differs: { decision: boolean; refund: boolean; reply: boolean }
}

/* ------------------------------------------------------------------ */
/* GET /api/metrics, GET /api/audit                                    */
/* ------------------------------------------------------------------ */

type Stats<T> = { mean: T | null; p50: T | null; p95: T | null; max: T | null }

export interface Metrics {
  cases: {
    total: number
    by_queue: Record<Queue, number>
    by_route: Record<Route, number>
    by_category: Record<Category, number>
    by_priority: Record<Priority, number>
    by_outcome: Record<Outcome, number>
    by_channel: Record<string, number>
    by_language: Record<Language, number>
    by_workflow: Record<Workflow, number>
  }
  auto_resolve_rate: number | null
  holds: { total: number; by_reason: Record<HoldReason, number> }
  self_check: { first_draft_failed: number; held_self_check_failed: number; human_edits_refused: number }
  human: { approved: number; rejected: number; edited_and_approved: number; acknowledged: number; override_rate: number | null }
  sla: { as_of: IsoTime; open: number; overdue: number; due_within_24h: number; compliance: number | null; closed: number }
  turnaround_minutes: { mean: number | null; p50: number | null; p95: number | null }
  trends: { received_by_day: { date: string; total: number; by_category: Record<Category, number> }[] }
  refunds_myr: { auto_paid: Money; approved_paid: Money; awaiting: Money; rejected: Money }
  cost_myr: { total: Cost } & Stats<Cost>
  latency_ms: Stats<number>
  models: { extract: Record<string, number>; draft: Record<string, number> }
  throughput: { decided: number; first_at: IsoTime | null; last_at: IsoTime | null; per_hour: number | null }
}

export interface AuditLog {
  total: number
  limit: number
  offset: number
  facets: { actors: string[]; actions: string[] }
  /** Newest first. */
  items: AuditEvent[]
}

export interface AuditQuery {
  actor?: string
  action?: string | string[]
  complaint_id?: string
  since?: string
  until?: string
  people_only?: boolean
  limit?: number
  offset?: number
}

/* ------------------------------------------------------------------ */
/* Login and platform actions (POST /api/cases/{id}/<action>)          */
/* ------------------------------------------------------------------ */

export interface User {
  username: string
  full_name: string
  role: Role
  /** null = no limit (manager). Officer: on the refund. Fraud analyst: on the disputed transaction. */
  approval_limit_myr: Money | null
}

export interface LoginRequest {
  username: string
  password: string
}

export interface Login {
  token: string
  user: User
}

/** Request body per platform action. Every action returns the full CaseDetail (send-back: 202). */
export interface ActionBodies {
  approve: { reason?: string }
  reject: { reason: string }
  'edit-reply': { reply_text: string; reason: string }
  'send-back': { note: string }
  escalate: { reason: string; outcome?: FraudOutcome }
  'flag-sensitive': { reason: string }
  'second-tier-approve': { reason: string }
  'second-tier-reject': { reason: string }
  reassign: { username: string; reason?: string }
  acknowledge: { reason?: string }
  investigate: { note: string; kind: 'investigation' | 'recall_attempt' }
  'record-outcome': { outcome: FraudOutcome; reason: string }
}
export type CaseAction = keyof ActionBodies

/* ------------------------------------------------------------------ */
/* Intake: POST /complaints (docs/api.md, the organisers' contract)    */
/* ------------------------------------------------------------------ */

/** The six fields of a complaints.csv row. `received_at` is "2026-09-30 10:15" (Malaysia time). */
export interface ComplaintInput {
  complaint_id: string
  customer_id: string
  received_at: string
  channel: string
  subject: string
  text: string
}

export interface IntakeAck {
  complaint_id: string
  status: CaseStatus
}

/* ------------------------------------------------------------------ */
/* Errors                                                              */
/* ------------------------------------------------------------------ */

/** FastAPI request-validation issue (422 on bad input). */
export interface ValidationIssue {
  loc: (string | number)[]
  msg: string
  type: string
}

/**
 * Error bodies: `{detail: "..."}`; a refused reply `{detail: {error, problems}}`;
 * over a limit (403) `{detail: {error, why, limit, amount}}`; FastAPI validation `{detail: [...]}`.
 */
export interface ErrorBody {
  detail:
    | string
    | ValidationIssue[]
    | { error: string; problems?: string[]; why?: string; limit?: Money; amount?: Money }
}
