import { describe, expect, it } from 'vitest'
import { compareMoney, toCents } from './money'

describe('toCents', () => {
  it('reads backend money strings exactly', () => {
    expect(toCents('550.00')).toBe(55000n)
    expect(toCents('0.05')).toBe(5n)
    expect(toCents('4687.10')).toBe(468710n)
  })

  it('handles commas, missing decimals and one decimal place', () => {
    expect(toCents('1,383.2')).toBe(138320n)
    expect(toCents('12')).toBe(1200n)
  })

  it('is exact where floating point is not', () => {
    // 0.1 + 0.2 !== 0.3 in floats; cents never drift.
    expect(toCents('0.10') + toCents('0.20')).toBe(toCents('0.30'))
  })
})

describe('compareMoney (the approval-limit check)', () => {
  it('treats exactly the limit as within it', () => {
    expect(compareMoney('2000.00', '2000.00')).toBe(0)
  })

  it('is over by a single sen', () => {
    expect(compareMoney('2000.01', '2000.00')).toBe(1)
    expect(compareMoney('1999.99', '2000.00')).toBe(-1)
  })

  it('compares by value, not by text', () => {
    expect(compareMoney('900.00', '2000.00')).toBe(-1)
    expect(compareMoney('10000.00', '2000.00')).toBe(1)
  })
})
