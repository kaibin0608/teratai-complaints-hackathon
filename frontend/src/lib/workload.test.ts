import { describe, expect, it } from 'vitest'
import type { CaseListItem } from './types'
import { summariseWork } from './workload'
import { mytToMs } from './clock'

const NOW = mytToMs('2026-10-23T12:00:00')

function item(over: Partial<CaseListItem>): CaseListItem {
  return {
    complaint_id: 'CMP-1',
    queue: 'awaiting_approval',
    workflow: null,
    resolve_due_at: '2026-10-30T12:00:00',
    assigned_to: null,
    sensitive: false,
    ...over,
  } as CaseListItem
}

describe('summariseWork', () => {
  it('counts only open work, and ignores closed cases', () => {
    const list = [item({}), item({ complaint_id: 'CMP-2', queue: 'approved' }), item({ complaint_id: 'CMP-3', workflow: 'closed' })]
    expect(summariseWork(list, NOW).open).toBe(1)
  })

  it('lists overdue cases with the longest wait first', () => {
    const list = [
      item({ complaint_id: 'NEWER', resolve_due_at: '2026-10-22T12:00:00' }),
      item({ complaint_id: 'OLDER', resolve_due_at: '2026-10-01T12:00:00' }),
      item({ complaint_id: 'FUTURE', resolve_due_at: '2026-11-01T12:00:00' }),
    ]
    expect(summariseWork(list, NOW).overdue.map((c) => c.complaint_id)).toEqual(['OLDER', 'NEWER'])
  })

  it('finds sensitive cases nobody owns', () => {
    const list = [item({ complaint_id: 'OWNED', sensitive: true, assigned_to: 'officer1' }), item({ complaint_id: 'LOOSE', sensitive: true })]
    expect(summariseWork(list, NOW).unownedSensitive.map((c) => c.complaint_id)).toEqual(['LOOSE'])
  })

  it('groups the load by person, with unassigned under null', () => {
    const list = [
      item({ assigned_to: 'officer1', resolve_due_at: '2026-10-01T12:00:00' }),
      item({ complaint_id: 'B', assigned_to: 'officer1' }),
      item({ complaint_id: 'C' }),
    ]
    const { byPerson } = summariseWork(list, NOW)
    expect(byPerson.get('officer1')).toEqual({ open: 2, overdue: 1 })
    expect(byPerson.get(null)).toEqual({ open: 1, overdue: 0 })
  })
})
