/**
 * Frontend mirror of the backend contract.
 *
 * Source of truth: backend/contracts.py (Pydantic models, JSON-serialised) and the
 * data model / API in docs/PLAN.md. Change this file only when those change.
 * Sections marked PROVISIONAL follow PLAN.md tables that are not in contracts.py yet;
 * confirm them against the API when it lands.
 *
 * Wire formats (Pydantic v2 JSON):
 * - Money is a Decimal serialised as a string rounded to the sen, e.g. "550.00".
 * - Datetimes are naive Malaysia time (MYT, UTC+8) without an offset, e.g. "2026-09-30T10:15:00".
 *   Never parse them as UTC or browser-local time. Display as DD-MM-YYYY HH:MM:SS.
 * - Dates are "YYYY-MM-DD". Intake also accepts DD-MM-YYYY and DD/MM/YYYY.
 * - Costs are in RM.
 */

/* ------------------------------------------------------------------ */
/* Primitives                                                          */
/* ------------------------------------------------------------------ */

/** Decimal string rounded to the sen, e.g. "550.00". */
export type Money = string
/** Naive MYT datetime, e.g. "2026-09-30T10:15:00". */
export type MytDateTime = string
/** "YYYY-MM-DD". */
export type IsoDate = string
export type Username = string

/* ------------------------------------------------------------------ */
/* Literals (contracts.py)                                             */
/* ------------------------------------------------------------------ */

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

export const PRIORITIES = ['P1', 'P2', 'P3'] as const
export type Priority = (typeof PRIORITIES)[number]

export const LANGUAGES = ['EN', 'MS'] as const
export type Language = (typeof LANGUAGES)[number]

export const ROUTES = ['AUTO_RESOLVE', 'HUMAN_APPROVAL', 'FRAUD_TEAM'] as const
export type Route = (typeof ROUTES)[number]

export const MATCH_STATUSES = ['confident', 'ambiguous', 'none', 'not_applicable'] as const
export type MatchStatus = (typeof MATCH_STATUSES)[number]

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

export const RUN_KINDS = ['autonomous', 'reprocess'] as const
export type RunKind = (typeof RUN_KINDS)[number]

/** fee_schedule.csv fee_name. */
export const FEE_TYPES = [
  'Monthly service charge',
  'Debit card annual fee',
  'Credit card annual fee',
] as const
export type FeeType = (typeof FEE_TYPES)[number]

/** Dataset values (docs/data_dictionary.md); contracts.py keeps channel as a plain string. */
export const COMPLAINT_CHANNELS = [
  'App chat',
  'Email',
  'Call centre note',
  'Branch form',
  'Social media DM',
] as const
export type ComplaintChannel = (typeof COMPLAINT_CHANNELS)[number]

/* ------------------------------------------------------------------ */
/* Raw CSV rows carried in Evidence (starter/data.py)                  */
/* ------------------------------------------------------------------ */

/** customers.csv row. All values are strings; empty string means absent. */
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
}

/** accounts.csv row. */
export interface AccountRow {
  account_id: string
  customer_id: string
  product: string
  open_date: IsoDate
  status: string
  card_last4: string
}

/** transactions.csv row, plus `amount` and `time` added by starter/data.py load(). */
export interface TxnRow {
  txn_id: string
  txn_time: string
  account_id: string
  customer_id: string
  direction: 'DR' | 'CR'
  amount_myr: string
  channel: string
  merchant_or_counterparty: string
  counterparty_account: string
  counterparty_bank: string
  merchant_country: string
  card_last4: string
  auth_method: string
  status: string
  description: string
  amount: number
  time: MytDateTime
}

/** atm_journal.csv row. */
export interface AtmJournalRow {
  txn_id: string
  atm_id: string
  atm_location: string
  requested_myr: string
  dispensed_myr: string
  journal_status: string
}

/** fee_schedule.csv row. */
export interface FeeScheduleRow {
  fee_code: string
  fee_name: string
  product: string
  amount_myr: string
  waiver_rule: string
}

/* ------------------------------------------------------------------ */
/* Pipeline models (contracts.py)                                      */
/* ------------------------------------------------------------------ */

/** One row of complaints.csv, or one live-round complaint. */
export interface Complaint {
  complaint_id: string
  customer_id: string
  received_at: MytDateTime
  channel: string
  subject: string
  text: string
}

/** Validated LLM extraction. Raw clues only; code resolves dates and matches. */
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
  fee_type: FeeType | null
  /** "YYYY-MM" when explicit. */
  fee_month: string | null
}

export interface Candidate {
  txn_id: string
  /** 0..1 */
  score: number
  reasons: string[]
}

export interface MatchResult {
  status: MatchStatus
  /** Best candidate; also set when ambiguous (exported, but the case is held). */
  txn_id: string | null
  candidates: Candidate[]
  /** Final category; may differ from Clues.category after fallback. */
  category: Category
  category_revised: boolean
}

/** Snapshot of what the decision used. The self-check accepts only allowed_* in a reply. */
export interface Evidence {
  /** null when customer_id is unknown (hold: customer_not_found). */
  customer: CustomerRow | null
  accounts: AccountRow[]
  matched_txn: TxnRow | null
  /** e.g. the earlier charge of a duplicate. */
  related_txns: TxnRow[]
  reversal: TxnRow | null
  atm_journal: AtmJournalRow | null
  fee_schedule_row: FeeScheduleRow | null
  allowed_txn_ids: string[]
  allowed_amounts: Money[]
}

export interface Calculation {
  /** e.g. "1500.00 requested − 950.00 dispensed = 550.00". */
  explanation: string
  inputs: Record<string, string>
}

/** The agent's decision. Field names match the predictions.csv columns. */
export interface Decision {
  category: Category
  matched_txn_id: string | null
  outcome: Outcome
  refund_amount_myr: Money
  priority: Priority
  reply_language: Language
  /** Final route, including any hold; this is exported. */
  route: Route
  /** Route from the policy before any hold. */
  policy_route: Route
  /** "CATEGORY.RULE", e.g. "ATM.SHORTFALL_REFUND". */
  rule_id: string
  calculation: Calculation
  hold_reason: HoldReason | null
  /** 65+ on received_at. */
  vulnerable: boolean
  ack_due_at: MytDateTime | null
  resolve_due_at: MytDateTime | null
}

export interface CheckResult {
  passed: boolean
  problems: string[]
  found_txn_ids: string[]
  found_amounts: Money[]
}

export interface LLMUsage {
  provider: string
  model: string
  tokens_in: number
  tokens_out: number
  cost_myr: Money
  latency_ms: number
  retries: number
  cached: boolean
}

/** One immutable pipeline run. The autonomous run is what predictions.csv exports. */
export interface AgentRun {
  run_id: string
  complaint_id: string
  run_kind: RunKind
  clues: Clues | null
  match: MatchResult | null
  decision: Decision | null
  evidence: Evidence | null
  reply_text: string
  self_check: CheckResult | null
  redraft_count: number
  error: string | null
  extract_usage: LLMUsage
  draft_usage: LLMUsage[]
  prompt_version: string
  schema_version: string
  policy_version: string
  created_at: MytDateTime
}

/* ------------------------------------------------------------------ */
/* Workflow models (PLAN.md data model) — PROVISIONAL                  */
/* ------------------------------------------------------------------ */

export const CASE_STATUSES = [
  'processing',
  'failed',
  'pending',
  'escalated',
  'approved',
  'rejected',
  'sent_back',
  'investigating',
  'sent',
  'closed',
] as const
export type CaseStatus = (typeof CASE_STATUSES)[number]

export const ROLES = ['officer', 'fraud', 'manager'] as const
export type Role = (typeof ROLES)[number]

export interface User {
  username: Username
  full_name: string
  role: Role
  /** null = no limit (manager). */
  approval_limit_myr: Money | null
}

/** `cases` table: mutable workflow state. */
export interface CaseRecord {
  complaint_id: string
  customer_id: string
  received_at: MytDateTime
  channel: string
  subject: string
  text: string
  /** The run exported to predictions.csv; never changes. */
  autonomous_run_id: string
  /** Latest run (after send-back). */
  current_run_id: string
  status: CaseStatus
  final_outcome: Outcome | null
  final_refund_myr: Money | null
  final_reply_text: string | null
  final_self_check: 'pass' | 'flag' | null
  approved_by: Username | null
  approved_at: MytDateTime | null
  sensitive: boolean
  sensitive_reason: string | null
  assigned_to: Username | null
  escalated_to: Username | null
  ack_due_at: MytDateTime | null
  resolve_due_at: MytDateTime | null
  created_at: MytDateTime
  updated_at: MytDateTime
}

export const CASE_ACTIONS = [
  'ingest',
  'agent_run',
  'approve',
  'edit',
  'reject',
  'send_back',
  'escalate',
  'reassign',
  'acknowledge',
  'investigate',
  'record_outcome',
  'second_tier_approve',
  'second_tier_reject',
  'send',
] as const
export type CaseAction = (typeof CASE_ACTIONS)[number]

/** `case_events` table: append-only audit log. */
export interface CaseEvent {
  id: number
  complaint_id: string
  /** Username, or "agent". */
  actor: string
  action: CaseAction
  field: string | null
  old_value: string | null
  new_value: string | null
  reason: string | null
  self_check_result: 'pass' | 'flag' | null
  created_at: MytDateTime
}

/** `outbound_messages` table: simulated delivery. */
export interface OutboundMessage {
  id: number
  complaint_id: string
  kind: 'resolution' | 'holding_reply'
  reply_text: string
  /** Simulated refund executed with this message ("0.00" for holding replies). */
  refund_myr: Money
  /** Username, or "auto" for AUTO_RESOLVE. */
  authorised_by: string
  status: 'queued' | 'sent' | 'failed'
  created_at: MytDateTime
}

/** GET /api/cases/{id}: agent run + evidence + final action + audit trail + outbound. */
export interface CaseDetail {
  case: CaseRecord
  autonomous_run: AgentRun
  current_run: AgentRun
  events: CaseEvent[]
  outbound: OutboundMessage[]
}

/* ------------------------------------------------------------------ */
/* API payloads (PLAN.md §2.2–2.3) — PROVISIONAL                       */
/* ------------------------------------------------------------------ */

export const FRAUD_OUTCOMES = [
  'confirmed_fraud',
  'not_fraud',
  'recall_succeeded',
  'recall_failed',
] as const
export type FraudOutcome = (typeof FRAUD_OUTCOMES)[number]

export interface LoginRequest {
  username: Username
  password: string
}

export interface LoginResponse {
  token: string
  user: User
}

/** POST /api/intake: one complaint row, or CSV text with one or more rows. */
export type IntakeRequest = { complaint: Complaint } | { csv: string }

export interface IntakeResponse {
  complaint_ids: string[]
}

/** GET /api/cases filters; sorted by priority then SLA due. */
export interface CaseQuery {
  category?: Category
  priority?: Priority
  status?: CaseStatus
  route?: Route
  hold_reason?: HoldReason
}

/** Every action that changes the agent's decision carries a reason. */
export interface ReasonRequest {
  reason: string
}

export interface EditReplyRequest {
  reply_text: string
}

/** Reject sets the final outcome and a reply that must pass the self-check before anything is sent. */
export interface RejectRequest extends ReasonRequest {
  final_outcome: Outcome
  final_refund_myr: Money
  reply_text: string
}

export interface ReassignRequest extends ReasonRequest {
  to: Username
}

export interface InvestigateRequest {
  note: string
}

export interface RecordOutcomeRequest extends ReasonRequest {
  outcome: FraudOutcome
}

/** GET /api/metrics (manager only). */
export interface Metrics {
  throughput: number
  auto_resolve_rate: number
  sla_compliance: number
  override_rate: number
  self_check_catches: number
  cost_per_complaint_myr: Money
  latency_per_complaint_ms: number
}

export interface ApiError {
  detail: string
}
