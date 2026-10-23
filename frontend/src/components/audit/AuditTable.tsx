import { Link } from 'react-router'
import { describeEvent } from '@/lib/events'
import { formatIsoTime } from '@/lib/format'
import { paths } from '@/lib/paths'
import type { AuditEvent } from '@/lib/types'
import { useNameOf } from '@/hooks/useNameOf'

const COLUMNS = ['When', 'Who', 'What', 'Case', 'Detail'] as const

/** Newest first. Edited replies show their text, so a manager can see exactly what changed. */
export function AuditTable({ items }: { items: readonly AuditEvent[] }) {
  return (
    <div className="overflow-x-auto rounded-card border border-default">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-xs text-secondary">
          <tr>
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className="px-cell-x py-cell-y font-medium whitespace-nowrap">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {items.map((event) => (
            <AuditRow key={event.id} event={event} />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AuditRow({ event }: { event: AuditEvent }) {
  const nameOf = useNameOf()
  const { title, note, problems } = describeEvent(event)
  const replyText = typeof event.detail?.reply_text === 'string' ? event.detail.reply_text : null
  return (
    <tr className="align-top">
      <td className="px-cell-x py-cell-y whitespace-nowrap text-secondary tabular-nums">{formatIsoTime(event.created_at)}</td>
      <td className="px-cell-x py-cell-y whitespace-nowrap text-primary">{nameOf(event.actor)}</td>
      <td className="px-cell-x py-cell-y text-primary">{title}</td>
      <td className="px-cell-x py-cell-y whitespace-nowrap">
        <Link to={paths.case(event.complaint_id)} className="font-medium text-link hover:text-link-hover">
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
