import type { Money } from './types'

/** "1,234.5" → 123450n. Exact: money never goes through a float. */
export function toCents(value: Money): bigint {
  const negative = value.trim().startsWith('-')
  const [whole = '0', fraction = ''] = value.replace(/^[-+\s]+/, '').replace(/,/g, '').split('.')
  const cents = BigInt(whole || '0') * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2))
  return negative ? -cents : cents
}

/** Negative, zero or positive as `a` is less than, equal to or greater than `b`. */
export function compareMoney(a: Money, b: Money): number {
  const diff = toCents(a) - toCents(b)
  return diff < 0n ? -1 : diff > 0n ? 1 : 0
}
