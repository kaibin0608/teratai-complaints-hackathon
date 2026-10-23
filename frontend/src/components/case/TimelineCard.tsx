import { Card } from '@/components/shared/Card'
import { SimulatedBadge } from '@/components/shared/SimulatedBadge'
import { describeEvent } from '@/lib/events'
import { formatIsoTime, formatMoney } from '@/lib/format'
import type { AuditEvent, CaseDetail, IsoTime } from '@/lib/types'

type Entry =
  | { kind: 'event'; at: IsoTime; event: AuditEvent }
  | { kind: 'outbound'; at: IsoTime; message: CaseDetail['outbound'][number] }

/** Everything that happened to the case, oldest first: the audit events and the messages sent (simulated). */
export function TimelineCard({ detail }: { detail: CaseDetail }) {
  const entries: Entry[] = [
    ...detail.events.map((event): Entry => ({ kind: 'event', at: event.created_at, event })),
    ...detail.outbound.map((message): Entry => ({ kind: 'outbound', at: message.created_at, message })),
  ].sort((a, b) => a.at.localeCompare(b.at))

  return (
    <Card title="Timeline" aside={<span className="text-xs text-secondary">{entries.length} entries</span>}>
      <ol className="flex flex-col gap-4 border-l border-default pl-4">
        {entries.map((entry) => (
          <li key={entry.kind === 'event' ? `e${entry.event.id}` : `o${entry.message.created_at}${entry.message.kind}`} className="relative">
            <span aria-hidden className="absolute top-1.5 -left-[1.3rem] size-2 rounded-full border border-neutral-400 bg-card" />
            {entry.kind === 'event' ? <EventRow event={entry.event} /> : <OutboundRow message={entry.message} />}
          </li>
        ))}
      </ol>
    </Card>
  )
}

function Meta({ at, who }: { at: IsoTime; who: string }) {
  return (
    <p className="text-xs text-secondary tabular-nums">
      {who} · {formatIsoTime(at)}
    </p>
  )
}

function EventRow({ event }: { event: AuditEvent }) {
  const { title, note, problems } = describeEvent(event)
  return (
    <>
      <p className="text-sm font-medium text-primary">{title}</p>
      {note && <p className="text-sm text-body">{note}</p>}
      {problems.length > 0 && (
        <ul className="mt-1 list-disc pl-4 text-sm text-error-700">
          {problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      <Meta at={event.created_at} who={event.actor} />
    </>
  )
}

function OutboundRow({ message }: { message: CaseDetail['outbound'][number] }) {
  const holding = message.kind === 'holding_reply'
  const refund = message.refund_amount_myr !== '0.00'
  return (
    <>
      <p className="flex flex-wrap items-center gap-2 text-sm font-medium text-primary">
        {holding ? 'Holding reply sent to the customer' : 'Reply sent to the customer'}
        <SimulatedBadge />
      </p>
      {refund && <p className="text-sm text-body">Refund {formatMoney(message.refund_amount_myr)}</p>}
      <details className="mt-1">
        <summary className="cursor-pointer text-sm text-link select-none hover:text-link-hover">Show message</summary>
        <p className="mt-1 rounded-control bg-subtle px-3 py-2 text-sm whitespace-pre-line text-body">{message.reply_text}</p>
      </details>
      <Meta at={message.created_at} who={`authorised by ${message.authorised_by}`} />
    </>
  )
}
