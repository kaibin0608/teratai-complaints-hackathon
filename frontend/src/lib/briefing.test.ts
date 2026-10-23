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

  it('only says a sensitive case needs the manager while it is still waiting', () => {
    const waiting = buildBriefing(makeCase({ sensitive: true })).paragraphs.join(' ')
    expect(waiting).toContain('needs the manager')
    const resolved = buildBriefing(makeCase({ sensitive: true, queue: 'auto_resolved', sent: true })).paragraphs.join(' ')
    expect(resolved).not.toContain('needs the manager')
  })

  it('does not call a service complaint a failed match', () => {
    const detail = makeCase()
    detail.decision = { ...detail.decision!, category: 'SERVICE_QUALITY' }
    detail.evidence = detail.evidence && { ...detail.evidence, matched_txn: null }
    const briefing = buildBriefing(detail)
    expect(briefing.paragraphs.join(' ')).toContain('No transaction is involved')
    expect(briefing.paragraphs.join(' ')).not.toContain('couldn’t find')
    expect(briefing.steps.find((step) => step.label === 'Found the transaction')?.state).toBe('done')
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
