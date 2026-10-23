import type { ActionKey } from './actions'
import { homeFor, paths } from './paths'
import type { CaseListItem, CaseListQuery, User } from './types'

/**
 * Actions that finish a person's work on a case, so the next case that needs them opens.
 * The others (edit, flag, log, acknowledge, reassign) keep them here: they are mid-case.
 */
export const ADVANCING: ReadonlySet<ActionKey> = new Set<ActionKey>([
  'approve',
  'reject',
  'send-back',
  'escalate',
  'second-tier-approve',
  'second-tier-reject',
  'record-outcome',
])

/** Where the next case that needs this person lives: first-tier users their own untouched queue, the manager escalations. */
export function nextCaseQuery(action: ActionKey, user: User): CaseListQuery {
  const base = { sort: 'priority', limit: 10 } as const
  if (user.role === 'officer') return { ...base, queue: 'awaiting_approval', workflow: 'none' }
  if (user.role === 'fraud') return { ...base, queue: 'with_fraud_team', workflow: 'none' }
  if (action.startsWith('second-tier')) return { ...base, workflow: 'escalated' }
  return action === 'record-outcome' ? { ...base, queue: 'with_fraud_team', workflow: 'none' } : { ...base, queue: 'awaiting_approval', workflow: 'none' }
}

/** The first candidate that is not the case just finished, is not being re-run, and is not someone else's. */
export function pickNext(items: readonly CaseListItem[], finishedId: string, user: User): CaseListItem | undefined {
  return items.find(
    (item) =>
      item.complaint_id !== finishedId &&
      item.status === 'done' &&
      item.workflow !== 'reprocessing' &&
      (user.role === 'manager' || item.assigned_to === null || item.assigned_to === user.username),
  )
}

/** Where to go when nothing else is waiting. */
export function homeAfter(action: ActionKey, user: User): string {
  if (user.role !== 'manager') return homeFor[user.role]
  return action.startsWith('second-tier') ? paths.manager : paths.cases
}
