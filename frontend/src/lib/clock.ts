/**
 * Time helpers. Times from the backend are naive Malaysia time; SLA countdowns and "overdue"
 * are measured against the real current time converted to Malaysia time, never the browser's zone.
 */
import { parseMyt } from './format'
import type { IsoTime } from './types'

const MYT_OFFSET_MS = 8 * 60 * 60 * 1000

/** Epoch ms of a naive MYT datetime. */
export function mytToMs(value: IsoTime): number {
  const p = parseMyt(value)
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - MYT_OFFSET_MS
}

/** Naive MYT datetime ("YYYY-MM-DDTHH:MM:SS") of an epoch ms. */
export function msToMyt(ms: number): IsoTime {
  return new Date(ms + MYT_OFFSET_MS).toISOString().slice(0, 19)
}

/** Current time as naive Malaysia time. */
export function now(): IsoTime {
  return msToMyt(Date.now())
}

/** Milliseconds until `due` from now; negative when overdue. */
export function msUntil(due: IsoTime): number {
  return mytToMs(due) - Date.now()
}
