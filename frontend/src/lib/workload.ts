/**
 * What the manager needs to see about the open work, worked out from the case list: who holds what, what is late,
 * and what nobody owns. Pure, so the rules are tested; the list itself comes from the backend.
 */
import { mytToMs } from './clock'
import type { CaseListItem } from './types'

/** Still waiting for people: in an approval or fraud queue, and not closed on the platform. */
export const isOpenItem = (item: CaseListItem): boolean =>
  (item.queue === 'awaiting_approval' || item.queue === 'with_fraud_team') && item.workflow !== 'closed'

export interface PersonLoad {
  open: number
  overdue: number
}

export interface WorkSummary {
  open: number
  /** Past their resolve deadline, the one that has waited longest first. */
  overdue: CaseListItem[]
  /** Sensitive and open, with nobody assigned. */
  unownedSensitive: CaseListItem[]
  /** Open cases per assignee username; `null` is unassigned. */
  byPerson: ReadonlyMap<string | null, PersonLoad>
}

export function summariseWork(items: readonly CaseListItem[], nowMs: number): WorkSummary {
  const open = items.filter(isOpenItem)
  const isOverdue = (item: CaseListItem) => item.resolve_due_at !== null && mytToMs(item.resolve_due_at) < nowMs

  const byPerson = new Map<string | null, PersonLoad>()
  for (const item of open) {
    const load = byPerson.get(item.assigned_to) ?? { open: 0, overdue: 0 }
    load.open += 1
    if (isOverdue(item)) load.overdue += 1
    byPerson.set(item.assigned_to, load)
  }

  return {
    open: open.length,
    overdue: open.filter(isOverdue).sort((a, b) => mytToMs(a.resolve_due_at ?? '') - mytToMs(b.resolve_due_at ?? '')),
    unownedSensitive: open.filter((item) => item.sensitive && item.assigned_to === null),
    byPerson,
  }
}
