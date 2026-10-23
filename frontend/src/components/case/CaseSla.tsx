import { SLATimer } from '@/components/shared/SLATimer'
import { acknowledgedAt, isOpen } from '@/lib/case'
import type { CaseDetail } from '@/lib/types'

/** Acknowledge and resolve deadlines while people still have to act; hidden once the case is resolved. */
export function CaseSla({ detail }: { detail: CaseDetail }) {
  const { decision, complaint, events } = detail
  if (!decision || !isOpen(detail)) return null
  return (
    <>
      {decision.ack_due_at && (
        <SLATimer label="Ack" start={complaint.received_at} due={decision.ack_due_at} doneAt={acknowledgedAt(events)} />
      )}
      {decision.resolve_due_at && <SLATimer label="Resolve" start={complaint.received_at} due={decision.resolve_due_at} />}
    </>
  )
}
