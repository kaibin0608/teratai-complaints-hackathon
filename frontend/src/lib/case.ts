/** Case rules the UI derives from the backend's case detail (everything else comes ready-made). */
import type { AuditEvent, CaseDetail, IsoTime } from './types'

/** Still waiting for people: in an approval or fraud queue, and not closed on the platform. */
export function isOpen({ case: c }: CaseDetail): boolean {
  return (c.queue === 'awaiting_approval' || c.queue === 'with_fraud_team') && c.workflow !== 'closed'
}

/** A first-tier user still has to act: open, and not escalated or re-running. */
export function awaitsFirstTier(detail: CaseDetail): boolean {
  return isOpen(detail) && detail.case.workflow !== 'escalated' && detail.case.workflow !== 'reprocessing'
}

/** First action by a person: the moment the acknowledge SLA is met. */
export function acknowledgedAt(events: readonly AuditEvent[]): IsoTime | null {
  return events.find((event) => event.actor !== 'agent')?.created_at ?? null
}
