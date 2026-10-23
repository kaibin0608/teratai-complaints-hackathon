import { describe, expect, it } from 'vitest'
import { loadPolicy, parameterValue, parseFees, parseParameters, parseSla } from './policy'
import { CATEGORIES, PRIORITIES } from './types'

/** These read the REAL files in data/, so they fail if a policy file changes shape under the Policy page. */
describe('the bank policy files', () => {
  const policy = loadPolicy()

  it('has a decision rule for every complaint category, in the app\'s order', () => {
    expect(policy.rules.map((r) => r.category)).toEqual([...CATEGORIES])
    for (const rule of policy.rules) {
      expect(rule.covers).not.toBe('')
      expect(rule.decision).not.toBe('')
      expect(PRIORITIES).toContain(rule.basePriority)
    }
  })

  it('keeps the routing limit and ages the rest of the app relies on', () => {
    expect(parameterValue(policy, 'AUTO_REFUND_LIMIT_MYR')).toBe('RM500.00')
    expect(parameterValue(policy, 'VULNERABLE_AGE')).toBe('65 years')
    expect(parameterValue(policy, 'DEBIT_FEE_WAIVER_AGE')).toBe('60 years')
    expect(parameterValue(policy, 'DUPLICATE_WINDOW_MINUTES')).toBe('10 minutes')
    expect(parameterValue(policy, 'MATCH_WINDOW_DAYS')).toBe('45 days')
  })

  it('has acknowledge and resolve targets for every priority', () => {
    expect(policy.sla.map((s) => s.priority)).toEqual([...PRIORITIES])
    for (const row of policy.sla) {
      expect(row.acknowledgeHours).toBeGreaterThan(0)
      expect(row.resolveBusinessDays).toBeGreaterThan(0)
    }
  })

  it('lists the fee schedule with amounts and waiver rules', () => {
    expect(policy.fees.length).toBeGreaterThan(0)
    for (const fee of policy.fees) {
      expect(fee.fee).not.toBe('')
      expect(fee.amount).toMatch(/^\d+\.\d{2}$/)
      expect(fee.waiver).not.toBe('')
    }
  })
})

describe('parsing', () => {
  it('shows a written-out rule as its meaning, with no value', () => {
    const [routing] = parseParameters('parameter,value,meaning\nROUTING,see meaning,INVESTIGATE goes to the fraud team')
    expect(routing).toMatchObject({ label: 'Routing', value: '', meaning: 'INVESTIGATE goes to the fraud team' })
  })

  it('uses singular units and makes an unknown parameter readable', () => {
    const [one, other] = parseParameters('parameter,value,meaning\nMATCH_WINDOW_DAYS,1,x\nSOME_NEW_LIMIT,7,y')
    expect(one?.value).toBe('1 day')
    expect(other).toMatchObject({ label: 'Some new limit', value: '7' })
  })

  it('ignores a priority or category the app does not know instead of guessing', () => {
    expect(parseSla('priority,acknowledge_within_hours,resolve_within_business_days\nP1,2,3\nP9,1,1')).toHaveLength(1)
  })

  it('reads quoted cells with commas', () => {
    const [fee] = parseFees('fee_code,fee_name,product,amount_myr,waiver_rule\nX,Annual fee,"Savings, Plus",12.00,"Waived at 60, or older"')
    expect(fee).toMatchObject({ product: 'Savings, Plus', waiver: 'Waived at 60, or older' })
  })
})
