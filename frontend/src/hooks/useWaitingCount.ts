import { useEffect, useRef } from 'react'
import { casesApi } from '@/api/cases'
import { paths } from '@/lib/paths'
import type { CaseListQuery, Role } from '@/lib/types'
import { useApi } from './useApi'
import { useToast } from './useToast'

/** Slower than the queues themselves: a badge does not need to be instant. */
const POLL_MS = 10_000

/** What "waiting for you" means per role: cases nobody has picked up yet, in the place where that person starts them. */
const WAITING: Record<Role, { to: string; query: CaseListQuery; one: string; many: string }> = {
  officer: { to: paths.officer, query: { queue: 'awaiting_approval', workflow: 'none', limit: 1 }, one: 'new case is waiting for you', many: 'new cases are waiting for you' },
  fraud: { to: paths.fraud, query: { queue: 'with_fraud_team', workflow: 'none', limit: 1 }, one: 'new fraud case has arrived', many: 'new fraud cases have arrived' },
  manager: { to: paths.manager, query: { workflow: 'escalated', limit: 1 }, one: 'case was escalated to you', many: 'cases were escalated to you' },
}

/**
 * The count for the sidebar badge, polled. When it goes up, the bell gets a quiet entry (no toast: a busy queue
 * should not interrupt). The first load only sets the baseline.
 */
export function useWaitingCount(role: Role): { to: string; count: number | null } {
  const { to, query, one, many } = WAITING[role]
  const result = useApi(`waiting:${role}`, (signal) => casesApi.list(query, signal), { pollMs: POLL_MS, keepPrevious: true })
  const count = result.status === 'success' ? result.data.total : null
  const { record } = useToast()
  const previous = useRef<number | null>(null)

  useEffect(() => {
    if (count === null) return
    const before = previous.current
    previous.current = count
    if (before !== null && count > before) {
      const added = count - before
      record({ tone: 'info', title: `${added} ${added === 1 ? one : many}`, link: { label: 'Open', to } })
    }
  }, [count, one, many, record, to])

  return { to, count }
}
