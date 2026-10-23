import { CircleAlert, Download, Inbox, LoaderCircle, RotateCw, Search, X } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { controlClass } from '@/components/shared/FieldShell'
import { FilterSelect } from '@/components/shared/FilterSelect'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useAuditLog } from '@/hooks/useAuditLog'
import { downloadCsv } from '@/lib/csv'
import { cx } from '@/lib/cx'
import { actionLabel, describeEvent } from '@/lib/events'
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
  // Keep a chosen value in the menu even if the current results no longer list it.
  const withCurrent = (values: string[], current: string) => (current && !values.includes(current) ? [current, ...values] : values)
  const menu = (values: string[], current: string, label: (value: string) => string): [string, string][] =>
    withCurrent(values, current).map((value) => [value, label(value)])
  const active = [filters.actor, filters.action, filters.caseId.trim(), filters.since, filters.until, filters.peopleOnly].filter(Boolean).length

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect label="Who" anyLabel="Who: anyone" value={filters.actor || null} onChange={(value) => change({ actor: value ?? ANY })} options={menu(facets.actors, filters.actor, nameOf)} />
        <FilterSelect label="What" anyLabel="What: any action" className="w-44" value={filters.action || null} onChange={(value) => change({ action: value ?? ANY })} options={menu(facets.actions, filters.action, actionLabel)} />

        <div className="relative w-36">
          <Search size={16} aria-hidden className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-secondary" />
          <input
            type="text"
            value={filters.caseId}
            onChange={(event) => change({ caseId: event.target.value })}
            placeholder="Case ID"
            aria-label="Case ID"
            className={cx('h-9 w-full pl-9', controlClass)}
          />
        </div>

        <div className="flex items-center gap-1.5">
          <input type="date" aria-label="From date" value={filters.since} max={filters.until || undefined} onChange={(event) => change({ since: event.target.value })} className={cx('h-9 w-34', controlClass)} />
          <span aria-hidden className="text-secondary">
            –
          </span>
          <input type="date" aria-label="To date" value={filters.until} min={filters.since || undefined} onChange={(event) => change({ until: event.target.value })} className={cx('h-9 w-34', controlClass)} />
        </div>

        <label className="flex h-9 items-center gap-2 text-sm text-body">
          <input type="checkbox" checked={filters.peopleOnly} onChange={(event) => change({ peopleOnly: event.target.checked })} className="size-4 accent-brand-600" />
          People only
        </label>

        {active > 0 && (
          <button type="button" onClick={() => change({ actor: ANY, action: ANY, caseId: '', since: '', until: '', peopleOnly: false })} className="flex items-center gap-1 text-xs font-medium text-link hover:text-link-hover">
            <X size={12} aria-hidden />
            Clear ({active})
          </button>
        )}

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
