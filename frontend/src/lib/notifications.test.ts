import { describe, expect, it } from 'vitest'
import { makeCase, officer } from '@/test/fixtures'
import type { ActionKey } from './actions'
import { actionToast, withAdvance } from './notifications'
import { makeNameOf } from './people'

const nameOf = makeNameOf([officer])

/** Every action, checked at compile time: a new action without an entry here fails the typecheck. */
const EVERY_ACTION = {
  approve: true,
  reject: true,
  'edit-reply': true,
  'send-back': true,
  escalate: true,
  'flag-sensitive': true,
  'second-tier-approve': true,
  'second-tier-reject': true,
  reassign: true,
  acknowledge: true,
  investigate: true,
  'record-outcome': true,
} satisfies Record<ActionKey, true>
const CASE_ACTIONS = Object.keys(EVERY_ACTION) as ActionKey[]

describe('actionToast', () => {
  it('gives every action a message, except saving a reply (its self-check shows in the dialog)', () => {
    for (const action of CASE_ACTIONS) {
      const toast = actionToast(action, makeCase(), {}, nameOf)
      if (action === 'edit-reply') expect(toast).toBeNull()
      else expect(toast?.title).toContain('CMP-00001')
    }
  })

  it('names the refund that was sent on approval', () => {
    const toast = actionToast('approve', makeCase({ refund: '550.00' }), {}, nameOf)
    expect(toast).toMatchObject({ tone: 'success', title: 'Approved CMP-00001' })
    expect(toast?.description).toContain('RM550.00')
  })

  it('says when the approved reply is the edited one', () => {
    expect(actionToast('approve', makeCase({ draft: 'passed' }), {}, nameOf)?.title).toBe('Approved CMP-00001 with your edited reply')
  })

  it('makes clear a rejection sent nothing', () => {
    expect(actionToast('reject', makeCase(), { reason: 'x' }, nameOf)).toMatchObject({ tone: 'neutral', description: 'Nothing was sent to the customer.' })
  })

  it('names the person a case was handed to, never their username', () => {
    expect(actionToast('reassign', makeCase(), { username: 'officer1' }, nameOf)?.title).toBe('Assigned CMP-00001 to Aina Rahman')
  })

  it('tells a manager rejection on a fraud case apart from one on an approval case', () => {
    expect(actionToast('second-tier-reject', makeCase({ queue: 'with_fraud_team' }), {}, nameOf)?.description).toContain('back to the analyst')
    expect(actionToast('second-tier-reject', makeCase(), {}, nameOf)?.description).toContain('closed')
  })
})

describe('withAdvance', () => {
  it('says where you are now and links back to the case you finished', () => {
    const toast = withAdvance({ tone: 'success', title: 'Approved CMP-00001' }, 'CMP-00001', 'next-case', '/cases/CMP-00001')
    expect(toast.description).toBe('Showing the next case that needs you.')
    expect(toast.link).toEqual({ label: 'Open CMP-00001 again', to: '/cases/CMP-00001' })
  })
})
