import { describe, expect, it } from 'vitest'
import { makeCase } from '@/test/fixtures'
import { acknowledgedAt, ageOn, awaitsFirstTier, isOpen } from './case'
import { describeEvent } from './events'
import type { AuditEvent } from './types'

describe('ageOn (the 65+ vulnerable rule uses the received date)', () => {
  it('turns 65 on the birthday itself', () => {
    expect(ageOn('1961-09-30', '2026-09-29T23:59:00')).toBe(64)
    expect(ageOn('1961-09-30', '2026-09-30T00:00:00')).toBe(65)
  })

  it('is not fooled by the month', () => {
    expect(ageOn('1961-12-31', '2026-09-30T10:00:00')).toBe(64)
    expect(ageOn('1961-01-01', '2026-09-30T10:00:00')).toBe(65)
  })
})

describe('case state', () => {
  it('is open in an approval or fraud queue, until closed', () => {
    expect(isOpen(makeCase())).toBe(true)
    expect(isOpen(makeCase({ queue: 'with_fraud_team', workflow: 'investigating' }))).toBe(true)
    expect(isOpen(makeCase({ queue: 'with_fraud_team', workflow: 'closed' }))).toBe(false)
    expect(isOpen(makeCase({ queue: 'approved' }))).toBe(false)
    expect(isOpen(makeCase({ queue: 'auto_resolved' }))).toBe(false)
  })

  it('needs a first-tier user only when nobody has escalated or re-run it', () => {
    expect(awaitsFirstTier(makeCase())).toBe(true)
    expect(awaitsFirstTier(makeCase({ workflow: 'escalated' }))).toBe(false)
    expect(awaitsFirstTier(makeCase({ workflow: 'reprocessing' }))).toBe(false)
  })
})

const event = (extra: Partial<AuditEvent>): AuditEvent => ({
  id: 1,
  complaint_id: 'CMP-00001',
  actor: 'agent',
  action: 'ingest',
  run_id: null,
  detail: null,
  created_at: '2026-09-01T10:00:00',
  ...extra,
})

describe('acknowledgedAt: the moment the acknowledge SLA is met', () => {
  it('ignores the agent and takes the first person', () => {
    const events = [event({}), event({ id: 2, action: 'agent_run' }), event({ id: 3, actor: 'officer1', action: 'approve', created_at: '2026-09-01T12:00:00' })]
    expect(acknowledgedAt(events)).toBe('2026-09-01T12:00:00')
  })

  it('is null while only the agent has acted', () => {
    expect(acknowledgedAt([event({})])).toBeNull()
  })
})

describe('describeEvent', () => {
  it('puts the agent\'s route and hold in plain words', () => {
    const { title, note } = describeEvent(
      event({ action: 'agent_run', detail: { route: 'HUMAN_APPROVAL', hold_reason: 'ambiguous_match', error: null } }),
    )
    expect(title).toBe('Agent decided')
    expect(note).toBe('Routed to Officer approval · held: Ambiguous match')
  })

  it('carries a person\'s reason and a refused edit\'s problems', () => {
    const { note, problems } = describeEvent(
      event({ actor: 'officer1', action: 'edit_approve_refused', detail: { reason: 'friendlier', problems: ['amount RM999.00 is not in the evidence'] } }),
    )
    expect(note).toBe('friendlier')
    expect(problems).toEqual(['amount RM999.00 is not in the evidence'])
  })

  it('makes an unknown action readable instead of showing the raw name', () => {
    expect(describeEvent(event({ action: 'something_new_happened' })).title).toBe('Something new happened')
  })
})
