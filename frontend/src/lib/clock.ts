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

/*
 * The SLA clock. Complaints are dated July–September 2026, so their deadlines are measured on the complaints' own
 * calendar: VITE_SLA_NOW (frontend/.env, the live-round day) is "now" when the page loads, and the clock ticks on in
 * real time from there. Unset, it is the real time. Only SLA deadlines use it; real waits (an escalation's age) don't.
 */
const SLA_BASE = import.meta.env.VITE_SLA_NOW?.trim()
const SLA_OFFSET_MS = SLA_BASE ? mytToMs(SLA_BASE) - Date.now() : 0

/** Epoch ms on the SLA clock. */
export const slaNowMs = (): number => Date.now() + SLA_OFFSET_MS

/** The SLA clock's "now" as naive MYT, or undefined when it is the real time (the backend then uses its own clock). */
export const slaAsOf = (): IsoTime | undefined => (SLA_BASE ? msToMyt(slaNowMs()) : undefined)

/** A real naive-MYT time moved onto the SLA clock. */
export const toSlaTime = (real: IsoTime): IsoTime => (SLA_OFFSET_MS ? msToMyt(mytToMs(real) + SLA_OFFSET_MS) : real)

/** Milliseconds until `due` on the SLA clock; negative when overdue. */
export function msUntil(due: IsoTime): number {
  return mytToMs(due) - slaNowMs()
}
