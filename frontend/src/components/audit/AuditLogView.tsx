import { CircleAlert, Download, Inbox, LoaderCircle, RotateCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { SelectField } from '@/components/shared/SelectField'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { TextField } from '@/components/shared/TextField'
import { useAuditLog } from '@/hooks/useAuditLog'
import { downloadCsv } from '@/lib/csv'
import { describeEvent } from '@/lib/events'
import { formatIsoTime } from '@/lib/format'
import type { AuditEvent, AuditQuery } from '@/lib/types'
import { AuditTable } from './AuditTable'
import { useNameOf } from '@/hooks/useNameOf'
import type { NameOf } from '@/lib/people'

const PAGE_SIZE = 100
const ANY = ''

interface Filters {
  actor: string
  action: string
  caseId: string
  /** "YYYY-MM-DD"; the backend reads a bare `until` as the end of that day. */
  since: string
  until: string
  peopleOnly: boolean
}

/** The append-only log: who did what, when, why. Filters come from the log's own `facets`. */
export function AuditLogView() {
  const [filters, setFilters] = useState<Filters>({ actor: ANY, action: ANY, caseId: '', since: '', until: '', peopleOnly: false })
  const [limit, setLimit] = useState(PAGE_SIZE)

  const query: AuditQuery = {
    actor: filters.actor || undefined,
    action: filters.action || undefined,
    complaint_id: filters.caseId.trim() || undefined,
    since: filters.since || undefined,
    until: filters.until || undefined,
    people_only: filters.peopleOnly || undefined,
    limit,
  }
  const result = useAuditLog(query)
  const nameOf = useNameOf()
  const change = (patch: Partial<Filters>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setLimit(PAGE_SIZE)
  }

  const facets = result.status === 'success' ? result.data.facets : { actors: [], actions: [] }
  const withCurrent = (values: string[], current: string) => (current && !values.includes(current) ? [current, ...values] : values)
  const options = (values: string[], current: string, any: string, label: (value: string) => string = (value) => value) => [
    { value: ANY, label: any },
    ...withCurrent(values, current).map((value) => ({ value, label: label(value) })),
  ]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-52">
          <SelectField label="Who" value={filters.actor} onChange={(e) => change({ actor: e.target.value })} options={options(facets.actors, filters.actor, 'Anyone', nameOf)} />
        </div>
        <div className="w-52">
          <SelectField
            label="What"
            value={filters.action}
            onChange={(e) => change({ action: e.target.value })}
            options={options(facets.actions, filters.action, 'Any action')}
          />
        </div>
        <div className="w-44">
          <TextField label="Case" placeholder="CMP-00244" value={filters.caseId} onChange={(e) => change({ caseId: e.target.value })} />
        </div>
        <div className="w-40">
          <TextField label="From" type="date" required={false} value={filters.since} max={filters.until || undefined} onChange={(e) => change({ since: e.target.value })} />
        </div>
        <div className="w-40">
          <TextField label="To" type="date" required={false} value={filters.until} min={filters.since || undefined} onChange={(e) => change({ until: e.target.value })} />
        </div>
        <label className="flex h-9 items-center gap-2 text-sm text-body">
          <input type="checkbox" checked={filters.peopleOnly} onChange={(e) => change({ peopleOnly: e.target.checked })} className="size-4 accent-brand-600" />
          People only
        </label>
        <div className="ml-auto">
          <ExportButton result={result} />
        </div>
      </div>

      <Body result={result} onMore={() => setLimit((l) => l + PAGE_SIZE)} />
    </div>
  )
}

type Result = ReturnType<typeof useAuditLog>

function ExportButton({ result }: { result: Result }) {
  const nameOf = useNameOf()
  const items = result.status === 'success' ? result.data.items : []
  return (
    <Button disabled={items.length === 0} onClick={() => downloadCsv('audit-log.csv', toRows(items, nameOf))}>
      <Download size={16} aria-hidden />
      Export CSV
    </Button>
  )
}

function toRows(items: readonly AuditEvent[], nameOf: NameOf) {
  const header = ['id', 'when', 'actor', 'action', 'case', 'detail', 'problems']
  return [
    header,
    ...items.map((event) => {
      const { title, note, problems } = describeEvent(event)
      return [event.id, formatIsoTime(event.created_at), nameOf(event.actor), title, event.complaint_id, note, problems.join('; ')]
    }),
  ]
}

function Body({ result, onMore }: { result: Result; onMore: () => void }) {
  if (result.status === 'loading') return <StatusMessage busy icon={LoaderCircle} title="Loading the log…" />
  if (result.status === 'error') {
    return (
      <StatusMessage
        icon={CircleAlert}
        title="Could not load the audit log"
        action={
          <Button onClick={result.reload}>
            <RotateCw size={16} aria-hidden />
            Retry
          </Button>
        }
      >
        {result.error.message}
      </StatusMessage>
    )
  }
  const { items, total } = result.data
  if (items.length === 0) return <StatusMessage icon={Inbox} title="No entries match" />
  return (
    <>
      <p className="text-xs text-secondary">
        Showing {items.length} of {total}, newest first. Entries can only be added, never changed.
      </p>
      <AuditTable items={items} />
      {items.length < total && (
        <div className="flex justify-center">
          <Button onClick={onMore}>Load more ({total - items.length} left)</Button>
        </div>
      )}
    </>
  )
}
