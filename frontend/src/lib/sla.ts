import { mytToMs } from './clock'
import type { IsoTime } from './types'

export type SlaState = 'on_track' | 'at_risk' | 'breached'

/** Below this share of the SLA window left, a case is "at risk" (PLAN.md: amber under 35%). */
const AT_RISK_SHARE = 0.35

export interface SlaStatus {
  state: SlaState
  /** Negative when breached. */
  remainingMs: number
}

/** SLA state of a deadline measured on the demo clock; the window runs from `start` (received_at) to `due`. */
export function slaStatus(start: IsoTime, due: IsoTime, nowMs: number): SlaStatus {
  const dueMs = mytToMs(due)
  const remainingMs = dueMs - nowMs
  if (remainingMs <= 0) return { state: 'breached', remainingMs }
  const windowMs = dueMs - mytToMs(start)
  const atRisk = windowMs > 0 && remainingMs / windowMs < AT_RISK_SHARE
  return { state: atRisk ? 'at_risk' : 'on_track', remainingMs }
}
