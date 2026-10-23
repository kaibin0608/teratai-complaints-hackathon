import { describe, expect, it } from 'vitest'
import { buildBriefing, suggestionsFor } from './briefing'
import { makeCase } from '@/test/fixtures'

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

describe('suggestionsFor', () => {
  it('always offers the basic question, at most four, without repeats', () => {
    const list = suggestionsFor(makeCase({ refund: '550.00', sensitive: true }))
    expect(list[0]).toBe('Why this decision?')
    expect(list.length).toBeLessThanOrEqual(4)
    expect(new Set(list).size).toBe(list.length)
  })
})
