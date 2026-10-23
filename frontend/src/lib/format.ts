/**
 * Display formatting for the backend's wire formats (see types.ts).
 *
 * Money stays a string end to end: no float conversion, so sen are never lost.
 * MYT datetimes are parsed by their parts, never through `new Date(string)`,
 * which would read them as UTC or browser-local time.
 */
import type { IsoDate, Money, IsoTime } from './types'

/** "1240.5" → "RM1,240.50"; "-12" → "-RM12.00". */
export function formatMoney(value: Money): string {
  const trimmed = value.trim()
  const negative = trimmed.startsWith('-')
  const [whole = '0', fraction = ''] = trimmed.replace(/^[-+]/, '').replace(/,/g, '').split('.')
  const grouped = whole.replace(/^0+(?=\d)/, '').replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  return `${negative ? '-' : ''}RM${grouped}.${fraction.padEnd(2, '0').slice(0, 2)}`
}

export interface MytParts {
  year: number
  month: number
  day: number
  hour: number
  minute: number
  second: number
}

const MYT_PATTERN = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/

/** Parse "YYYY-MM-DD" or "YYYY-MM-DD[T ]HH:MM[:SS]" (naive MYT) into its parts. */
export function parseMyt(value: IsoTime | IsoDate): MytParts {
  const match = MYT_PATTERN.exec(value.trim())
  if (!match) throw new Error(`Unrecognised MYT datetime: ${value}`)
  const [, year, month, day, hour = '0', minute = '0', second = '0'] = match
  return {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second),
  }
}

const pad = (n: number) => String(n).padStart(2, '0')

/** Bank format (UI_API.md): "2026-09-30T10:15:00" → "30-09-2026 10:15"; with `seconds`, "30-09-2026 10:15:00". */
export function formatIsoTime(value: IsoTime, { seconds = false } = {}): string {
  const p = parseMyt(value)
  const time = `${pad(p.hour)}:${pad(p.minute)}${seconds ? `:${pad(p.second)}` : ''}`
  return `${pad(p.day)}-${pad(p.month)}-${p.year} ${time}`
}

/** Compact duration, sign ignored: "2d 4h", "3h 15m", "12m", "<1m". */
export function formatDuration(ms: number): string {
  const minutes = Math.floor(Math.abs(ms) / 60_000)
  if (minutes < 1) return '<1m'
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  if (days > 0) return hours > 0 ? `${days}d ${hours}h` : `${days}d`
  if (hours > 0) return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  return `${mins}m`
}

/** 0.346 → "35%"; null (no data yet) → "–". */
export function formatPercent(rate: number | null): string {
  return rate === null ? '–' : `${Math.round(rate * 100)}%`
}

/** 3100 → "3.1 s", 850 → "850 ms"; null → "–". */
export function formatMs(ms: number | null): string {
  if (ms === null) return '–'
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`
}

/** A Cost string (RM, 4 decimals) as the backend sends it → "RM0.0013"; null → "–". */
export function formatCost(cost: string | null): string {
  return cost === null ? '–' : `RM${cost}`
}

/** "2026-09-30" (or a datetime) → "30-09-2026". */
export function formatMytDate(value: IsoDate | IsoTime): string {
  const p = parseMyt(value)
  return `${pad(p.day)}-${pad(p.month)}-${p.year}`
}
