/**
 * The bank's fixed policy, read from the same CSV files the backend applies (data/*.csv). The Policy page shows
 * it read-only; nothing here changes it. The files are read at build time, so there is a single source of truth
 * and no policy numbers are copied into the UI.
 */
import complaintPolicyCsv from '@data/complaint_policy.csv?raw'
import feeScheduleCsv from '@data/fee_schedule.csv?raw'
import policyParametersCsv from '@data/policy_parameters.csv?raw'
import slaPolicyCsv from '@data/sla_policy.csv?raw'
import { parseCsv } from './csv'
import { formatMoney } from './format'
import { CATEGORIES, PRIORITIES, type Category, type Priority } from './types'

export interface CategoryRule {
  category: Category
  covers: string
  howToFind: string
  decision: string
  basePriority: Priority
}

export interface PolicyParameter {
  key: string
  /** Plain-language name. */
  label: string
  /** Display value; empty for a parameter that is a rule written out in `meaning`. */
  value: string
  meaning: string
}

export interface FeeRow {
  code: string
  fee: string
  product: string
  amount: string
  /** "None" in the file means the fee is always charged. */
  waiver: string
}

export interface SlaRow {
  priority: Priority
  acknowledgeHours: number
  resolveBusinessDays: number
}

export interface Policy {
  rules: CategoryRule[]
  parameters: PolicyParameter[]
  fees: FeeRow[]
  sla: SlaRow[]
}

type Row = Record<string, string>

/** CSV text → one object per row, keyed by the header. */
function table(csv: string): Row[] {
  const [head = [], ...rows] = parseCsv(csv)
  return rows.map((cells) => Object.fromEntries(head.map((name, i) => [name.trim(), (cells[i] ?? '').trim()])))
}

const withUnit = (unit: string) => (value: string) => `${value} ${Number(value) === 1 ? unit : `${unit}s`}`

/** How each known parameter reads on screen. A parameter that is a written-out rule has no value to show. */
const PARAMETERS: Record<string, { label: string; show: (value: string) => string }> = {
  AUTO_REFUND_LIMIT_MYR: { label: 'Auto-refund limit', show: formatMoney },
  VULNERABLE_AGE: { label: 'Vulnerable customer age', show: withUnit('year') },
  DEBIT_FEE_WAIVER_AGE: { label: 'Debit card fee waiver age', show: withUnit('year') },
  DUPLICATE_WINDOW_MINUTES: { label: 'Duplicate charge window', show: withUnit('minute') },
  MATCH_WINDOW_DAYS: { label: 'Transaction search window', show: withUnit('day') },
  ROUTING: { label: 'Routing', show: () => '' },
  REPLY_LANGUAGE: { label: 'Reply language', show: () => '' },
}

const humanise = (key: string) => {
  const words = key.toLowerCase().replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function parseCategoryRules(csv: string): CategoryRule[] {
  const byCategory = new Map(table(csv).map((row) => [row.category, row]))
  // In the order the app uses everywhere; a category the app does not know is ignored, not guessed at.
  return CATEGORIES.flatMap((category) => {
    const row = byCategory.get(category)
    const basePriority = PRIORITIES.find((p) => p === row?.base_priority)
    if (!row || !basePriority) return []
    return [{ category, covers: row.what_it_covers ?? '', howToFind: row.how_to_find_the_transaction ?? '', decision: row.decision_rule ?? '', basePriority }]
  })
}

export function parseParameters(csv: string): PolicyParameter[] {
  return table(csv).map(({ parameter = '', value = '', meaning = '' }) => {
    const known = PARAMETERS[parameter]
    return { key: parameter, label: known?.label ?? humanise(parameter), value: known ? known.show(value) : value, meaning }
  })
}

export function parseFees(csv: string): FeeRow[] {
  return table(csv).map((row) => ({
    code: row.fee_code ?? '',
    fee: row.fee_name ?? '',
    product: row.product ?? '',
    amount: row.amount_myr ?? '0.00',
    waiver: row.waiver_rule ?? '',
  }))
}

export function parseSla(csv: string): SlaRow[] {
  return table(csv).flatMap((row) => {
    const priority = PRIORITIES.find((p) => p === row.priority)
    return priority
      ? [{ priority, acknowledgeHours: Number(row.acknowledge_within_hours), resolveBusinessDays: Number(row.resolve_within_business_days) }]
      : []
  })
}

export const loadPolicy = (): Policy => ({
  rules: parseCategoryRules(complaintPolicyCsv),
  parameters: parseParameters(policyParametersCsv),
  fees: parseFees(feeScheduleCsv),
  sla: parseSla(slaPolicyCsv),
})

/** One parameter's display value, e.g. `parameterValue(policy, 'AUTO_REFUND_LIMIT_MYR')` → "RM500.00". */
export const parameterValue = (policy: Policy, key: string): string => policy.parameters.find((p) => p.key === key)?.value ?? '–'
