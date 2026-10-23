import { describe, expect, it } from 'vitest'
import { buildBriefing, recommendedAction, suggestionsFor } from './briefing'
import { makeNameOf } from './people'
import { makeCase, officer } from '@/test/fixtures'

const nameOf = makeNameOf([officer])

describe('buildBriefing', () => {
  it('says what it recommends and why a person is needed', () => {
    const text = buildBriefing(makeCase({ refund: '550.00' })).paragraphs.join(' ')
    expect(text).toContain('I recommend a refund of RM550.00')
    expect(text).toContain('officer approval')
  })

  it('says plainly when it is still working', () => {
    const detail = makeCase()
    detail.case.status = 'processing'
    expect(buildBriefing(detail).paragraphs[0]).toContain('still working')
  })

  it('lists the steps behind the briefing', () => {
    const steps = buildBriefing(makeCase()).steps.map((step) => step.label)
    expect(steps).toEqual(expect.arrayContaining(['Read the complaint', 'Found the transaction', 'Applied the policy', 'Chose the route']))
  })
})

describe('recommendedAction', () => {
  it('points at Approve when the agent is sure and the refund is within the limit', () => {
    expect(recommendedAction(makeCase({ refund: '100.00' }), officer, nameOf)).toBe('approve')
  })

  it('points at Escalate instead when the refund is over the officer’s limit', () => {
    expect(recommendedAction(makeCase({ refund: '3000.00' }), officer, nameOf)).toBe('escalate')
  })

  it('points at nothing when the agent held the case for review', () => {
    const detail = makeCase()
    if (detail.decision) detail.decision.hold_reason = 'ambiguous_match'
    expect(recommendedAction(detail, officer, nameOf)).toBeNull()
  })

  it('points at nothing once the case is closed', () => {
    expect(recommendedAction(makeCase({ queue: 'approved', workflow: 'closed' }), officer, nameOf)).toBeNull()
  })
})

describe('suggestionsFor', () => {
  it('always offers the basic question, at most four, without repeats', () => {
    const list = suggestionsFor(makeCase({ refund: '550.00', sensitive: true }))
    expect(list[0]).toBe('Why this decision?')
    expect(list.length).toBeLessThanOrEqual(4)
    expect(new Set(list).size).toBe(list.length)
  })
})
