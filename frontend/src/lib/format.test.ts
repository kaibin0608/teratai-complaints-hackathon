import { describe, expect, it } from 'vitest'
import { mytToMs, msToMyt } from './clock'
import { formatDuration, formatIsoTime, formatMoney, formatMs, formatMytDate, formatPercent, parseMyt } from './format'
import { slaStatus } from './sla'

describe('formatMoney', () => {
  it('formats the backend\'s strings without touching a float', () => {
    expect(formatMoney('550.00')).toBe('RM550.00')
    expect(formatMoney('1240.5')).toBe('RM1,240.50')
    expect(formatMoney('4687.10')).toBe('RM4,687.10')
    expect(formatMoney('0.00')).toBe('RM0.00')
    expect(formatMoney('-12')).toBe('-RM12.00')
  })
})

describe('Malaysia-time strings', () => {
  it('formats in the bank style, by parts (no time-zone shift)', () => {
    expect(formatIsoTime('2026-09-30T10:15:00')).toBe('30-09-2026 10:15')
    expect(formatIsoTime('2026-09-30T10:15:42', { seconds: true })).toBe('30-09-2026 10:15:42')
    expect(formatIsoTime('2026-04-01 03:11:04')).toBe('01-04-2026 03:11')
    expect(formatMytDate('2026-03-10')).toBe('10-03-2026')
  })

  it('refuses input that is not a backend date', () => {
    expect(() => parseMyt('30/09/2026')).toThrow()
  })

  it('converts to and from epoch milliseconds without drift', () => {
    expect(msToMyt(mytToMs('2026-09-30T10:15:00'))).toBe('2026-09-30T10:15:00')
    expect(mytToMs('2026-09-30T08:00:00')).toBe(Date.UTC(2026, 8, 30, 0, 0, 0))
  })
})

describe('numbers for dashboards', () => {
  it('shows "–" for a missing rate, not 0', () => {
    expect(formatPercent(null)).toBe('–')
    expect(formatPercent(0.346)).toBe('35%')
    expect(formatMs(null)).toBe('–')
    expect(formatMs(850)).toBe('850 ms')
    expect(formatMs(3100)).toBe('3.1 s')
  })

  it('shortens durations', () => {
    expect(formatDuration(30_000)).toBe('<1m')
    expect(formatDuration(12 * 60_000)).toBe('12m')
    expect(formatDuration(195 * 60_000)).toBe('3h 15m')
    expect(formatDuration(26 * 3600_000)).toBe('1d 2h')
    expect(formatDuration(-5 * 3600_000)).toBe('5h')
  })
})

describe('slaStatus ', () => {
  const now = mytToMs('2026-09-30T10:00:00')

  it('is on track with plenty of time left', () => {
    expect(slaStatus('2026-09-30T09:00:00', '2026-09-30T20:00:00', now).state).toBe('on_track')
  })

  it('is at risk below 35% of the window', () => {
    // window 22:00 → 12:00 is 14 h; 2 h left is 14%.
    expect(slaStatus('2026-09-29T22:00:00', '2026-09-30T12:00:00', now).state).toBe('at_risk')
  })

  it('is breached at the deadline itself, and after it', () => {
    expect(slaStatus('2026-09-30T08:00:00', '2026-09-30T10:00:00', now).state).toBe('breached')
    expect(slaStatus('2026-09-28T10:00:00', '2026-09-30T05:00:00', now).state).toBe('breached')
  })
})
