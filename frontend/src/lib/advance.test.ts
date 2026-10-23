import { describe, expect, it } from 'vitest'
import { fraudAnalyst, manager, officer } from '@/test/fixtures'
import { ADVANCING, doneMessage, homeAfter, nextCaseQuery, pickNext } from './advance'
import { paths } from './paths'
import type { CaseListItem } from './types'

const item = (id: string, extra: Partial<CaseListItem> = {}) =>
  ({ complaint_id: id, status: 'done', workflow: null, assigned_to: null, ...extra }) as CaseListItem

describe('which actions move on to the next case', () => {
  it('advances when the person is finished with the case', () => {
    for (const action of ['approve', 'reject', 'send-back', 'escalate', 'second-tier-approve', 'second-tier-reject', 'record-outcome'] as const) {
      expect(ADVANCING.has(action)).toBe(true)
    }
  })

  it('stays when the person is mid-case', () => {
    for (const action of ['edit-reply', 'flag-sensitive', 'investigate', 'acknowledge', 'reassign'] as const) {
      expect(ADVANCING.has(action)).toBe(false)
    }
  })
})

describe('nextCaseQuery: where the next case that needs this person lives', () => {
  it('officer: untouched approval cases', () => {
    expect(nextCaseQuery('approve', officer)).toMatchObject({ queue: 'awaiting_approval', workflow: 'none', sort: 'priority' })
  })

  it('fraud analyst: fraud cases nobody has acknowledged', () => {
    expect(nextCaseQuery('record-outcome', fraudAnalyst)).toMatchObject({ queue: 'with_fraud_team', workflow: 'none' })
  })

  it('manager: the next escalation after a second-tier decision', () => {
    expect(nextCaseQuery('second-tier-approve', manager)).toMatchObject({ workflow: 'escalated' })
  })

  it('manager: otherwise the next approval case', () => {
    expect(nextCaseQuery('approve', manager)).toMatchObject({ queue: 'awaiting_approval', workflow: 'none' })
  })
})

describe('pickNext', () => {
  it('skips the case just finished', () => {
    expect(pickNext([item('A'), item('B')], 'A', officer)?.complaint_id).toBe('B')
  })

  it("skips cases that are re-running or assigned to someone else, for first-tier users", () => {
    const items = [item('A', { workflow: 'reprocessing' }), item('B', { assigned_to: 'officer2' }), item('C', { assigned_to: 'officer1' })]
    expect(pickNext(items, 'X', officer)?.complaint_id).toBe('C')
  })

  it("lets the manager take any case, including someone else's", () => {
    expect(pickNext([item('B', { assigned_to: 'officer2' })], 'X', manager)?.complaint_id).toBe('B')
  })

  it('skips cases the agent has not finished', () => {
    expect(pickNext([item('A', { status: 'processing' })], 'X', officer)).toBeUndefined()
  })

  it('returns nothing when the queue is clear', () => {
    expect(pickNext([], 'A', officer)).toBeUndefined()
    expect(pickNext([item('A')], 'A', officer)).toBeUndefined()
  })
})

describe('where to go, and what to say, afterwards', () => {
  it('sends each first-tier role to its own queue', () => {
    expect(homeAfter('approve', officer)).toBe(paths.officer)
    expect(homeAfter('record-outcome', fraudAnalyst)).toBe(paths.fraud)
  })

  it('sends the manager to the console after a second-tier decision, otherwise to all cases', () => {
    expect(homeAfter('second-tier-reject', manager)).toBe(paths.manager)
    expect(homeAfter('approve', manager)).toBe(paths.cases)
  })

  it('names what was done', () => {
    expect(doneMessage('approve', 'CMP-00244')).toBe('Approved CMP-00244.')
    expect(doneMessage('record-outcome', 'CMP-00138')).toBe('Recorded the outcome of CMP-00138.')
  })
})
