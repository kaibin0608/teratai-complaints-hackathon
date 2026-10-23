import { Bot } from 'lucide-react'
import { Link } from 'react-router'
import { useNameOf } from '@/hooks/useNameOf'
import { now } from '@/lib/clock'
import { describeEvent } from '@/lib/events'
import { parseMyt } from '@/lib/format'
import { paths } from '@/lib/paths'
import type { AuditEvent } from '@/lib/types'

const COLUMNS = ['Time', 'Who', 'What', 'Case', 'Detail'] as const

type Tone = 'neutral' | 'success' | 'error' | 'warning' | 'info'

/** The dot beside each action: grey for the agent's own steps, then by what a person did. Literal classes so Tailwind generates them. */
const TONE_DOT: Record<Tone, string> = {
  neutral: 'bg-neutral-300',
  success: 'bg-success-500',
  error: 'bg-error-500',
  warning: 'bg-warning-400',
  info: 'bg-info-400',
}

const ACTION_TONE: Record<string, Tone> = {
  ingest: 'neutral',
  agent_run: 'neutral',
  approve: 'success',
  edit_approve: 'success',
  second_tier_approve: 'success',
  record_outcome: 'success',
  reject: 'error',
  second_tier_reject: 'error',
  edit_approve_refused: 'error',
  send_back_failed: 'error',
  escalate: 'warning',
  flag_sensitive: 'warning',
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "Today", "Yesterday", or "Thu 17 Oct 2026". Dates are Malaysia time as given, never converted. */
function dayLabel(date: string, today: string): string {
  if (date === today) return 'Today'
  const p = parseMyt(date)
  const asDay = Date.UTC(p.year, p.month - 1, p.day)
  const t = parseMyt(today)
  if (asDay === Date.UTC(t.year, t.month - 1, t.day) - 86_400_000) return 'Yesterday'
  return `${WEEKDAYS[new Date(asDay).getUTCDay()]} ${p.day} ${MONTHS[p.month - 1]} ${p.year}`
}

/** Group newest-first events by calendar day, keeping their order. */
function byDay(items: readonly AuditEvent[]): { date: string; events: AuditEvent[] }[] {
  const days: { date: string; events: AuditEvent[] }[] = []
  for (const event of items) {
    const date = event.created_at.slice(0, 10)
    const last = days[days.length - 1]
    if (last?.date === date) last.events.push(event)
    else days.push({ date, events: [event] })
  }
  return days
}

/** Newest first, grouped by day. Edited replies show their text, so a manager can see exactly what changed. */
export function AuditTable({ items }: { items: readonly AuditEvent[] }) {
  const today = now().slice(0, 10)
  return (
    <div className="overflow-x-auto rounded-card border border-default">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-[11px] tracking-wide text-secondary uppercase">
          <tr>
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className="px-cell-x py-cell-y font-medium whitespace-nowrap">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        {byDay(items).map(({ date, events }) => (
          <tbody key={date} className="divide-y divide-neutral-100 border-t border-default">
            <tr className="bg-neutral-25">
              <th colSpan={COLUMNS.length} scope="colgroup" className="px-cell-x py-1.5 text-left text-xs font-semibold text-primary">
                {dayLabel(date, today)}
                <span className="ml-2 font-normal text-secondary tabular-nums">
                  {events.length} {events.length === 1 ? 'entry' : 'entries'}
                </span>
              </th>
            </tr>
            {events.map((event) => (
              <AuditRow key={event.id} event={event} />
            ))}
          </tbody>
        ))}
      </table>
    </div>
  )
}

function AuditRow({ event }: { event: AuditEvent }) {
  const nameOf = useNameOf()
  const { title, note, problems } = describeEvent(event)
  const replyText = typeof event.detail?.reply_text === 'string' ? event.detail.reply_text : null
  const agent = event.actor === 'agent'
  const tone = ACTION_TONE[event.action] ?? 'info'
  return (
    <tr className="align-top transition-colors hover:bg-subtle">
      <td className="px-cell-x py-cell-y whitespace-nowrap text-secondary tabular-nums" title={event.created_at.replace('T', ' ')}>
        {event.created_at.slice(11, 16)}
      </td>
      <td className="px-cell-x py-cell-y whitespace-nowrap">
        {agent ? (
          <span className="inline-flex items-center gap-1.5 text-secondary">
            <Bot size={14} aria-hidden />
            Agent
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 text-primary">
            <span aria-hidden className="grid size-5 place-items-center rounded-full bg-brand-100 text-[10px] font-semibold text-brand-800">
              {initials(nameOf(event.actor))}
            </span>
            {nameOf(event.actor)}
          </span>
        )}
      </td>
      <td className="px-cell-x py-cell-y text-primary">
        <span className="inline-flex items-start gap-2">
          <span aria-hidden className={`mt-1.5 size-2 shrink-0 rounded-full ${TONE_DOT[tone]}`} />
          {title}
        </span>
      </td>
      <td className="px-cell-x py-cell-y whitespace-nowrap">
        <Link to={paths.case(event.complaint_id)} className="text-body underline decoration-neutral-300 underline-offset-2 hover:text-link hover:decoration-current">
          {event.complaint_id}
        </Link>
      </td>
      <td className="px-cell-x py-cell-y">
        {note && <p className="text-body">{note}</p>}
        {problems.length > 0 && (
          <ul className="list-disc pl-4 text-error-700">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        )}
        {replyText && (
          <details className="mt-1">
            <summary className="cursor-pointer text-link select-none hover:text-link-hover">Show reply text</summary>
            <p className="mt-1 rounded-control bg-subtle px-3 py-2 whitespace-pre-line text-body">{replyText}</p>
          </details>
        )}
      </td>
    </tr>
  )
}

const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word.charAt(0).toUpperCase())
    .join('')
