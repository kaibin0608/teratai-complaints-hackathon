/**
 * Demo clock (PLAN.md: "a labelled demo clock (e.g. 2026-09-30) so historical data isn't all overdue").
 *
 * At page load the clock is set to DEMO_DATE at the current Malaysia time of day, then it
 * ticks in real time. SLA countdowns and "overdue" are measured against it, never Date.now().
 */
import { parseMyt } from './format'
import type { IsoDate, IsoTime } from './types'

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

export const DEMO_DATE: IsoDate = import.meta.env.VITE_DEMO_DATE ?? '2026-09-30'

const clockOffsetMs = (() => {
  const realNow = Date.now()
  const timeOfDay = msToMyt(realNow).slice(10)
  return mytToMs(`${DEMO_DATE}${timeOfDay}`) - realNow
})()

/** Current demo time, epoch ms. */
export function demoNowMs(): number {
  return Date.now() + clockOffsetMs
}

/** Current demo time as naive MYT. */
export function demoNow(): IsoTime {
  return msToMyt(demoNowMs())
}

/** Milliseconds until `due` on the demo clock; negative when overdue. */
export function msUntil(due: IsoTime): number {
  return mytToMs(due) - demoNowMs()
}
