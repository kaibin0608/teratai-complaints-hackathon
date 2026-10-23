import { describe, expect, it } from 'vitest'
import { fraudAnalyst, makeCase, manager, officer } from '@/test/fixtures'
import { planActions, type ActionPlan, type ActionKey } from './actions'

const keys = (plan: ActionPlan): ActionKey[] => plan.actions.map((a) => a.key)
const primary = (plan: ActionPlan): ActionKey | undefined => plan.actions.find((a) => a.emphasis === 'primary')?.key

describe('officer on an approval case', () => {
  it('approves a refund within the limit', () => {
    const plan = planActions(makeCase({ refund: '550.00' }), officer)
    expect(primary(plan)).toBe('approve')
    expect(plan.limit?.over).toBe(false)
  })

  it('treats exactly RM2,000.00 as within the limit', () => {
    const plan = planActions(makeCase({ refund: '2000.00' }), officer)
    expect(primary(plan)).toBe('approve')
  })

  it('must escalate RM2,000.01: Escalate is the main action and Approve is gone', () => {
    const plan = planActions(makeCase({ refund: '2000.01' }), officer)
    expect(primary(plan)).toBe('escalate')
    expect(keys(plan)).not.toContain('approve')
    expect(plan.limit?.over).toBe(true)
    expect(plan.notice).toMatch(/over your limit/)
  })

  it('must escalate a sensitive case whatever the amount', () => {
    const plan = planActions(makeCase({ refund: '10.00', sensitive: true }), officer)
    expect(primary(plan)).toBe('escalate')
    expect(keys(plan)).not.toContain('approve')
    expect(keys(plan)).not.toContain('flag-sensitive')
    expect(plan.notice).toMatch(/Sensitive/)
  })

  it('locks Approve while the edited draft fails the self-check', () => {
    const approve = planActions(makeCase({ draft: 'flagged' }), officer).actions.find((a) => a.key === 'approve')
    expect(approve?.disabledReason).toMatch(/self-check/)
  })

  it('unlocks Approve once the edited draft passes, even if the agent reply had failed', () => {
    const approve = planActions(makeCase({ replyPassed: false, draft: 'passed' }), officer).actions.find((a) => a.key === 'approve')
    expect(approve?.disabledReason).toBeUndefined()
  })

  it('locks Approve when the agent reply fails and nobody has edited it', () => {
    const approve = planActions(makeCase({ replyPassed: false }), officer).actions.find((a) => a.key === 'approve')
    expect(approve?.disabledReason).toBeDefined()
  })

  it('has no buttons on a case assigned to someone else', () => {
    const plan = planActions(makeCase({ assignedTo: 'officer2' }), officer)
    expect(plan.actions).toEqual([])
    expect(plan.notice).toMatch(/officer2/)
  })

  it('may act on a case assigned to them', () => {
    expect(keys(planActions(makeCase({ assignedTo: 'officer1' }), officer))).toContain('approve')
  })

  it('cannot reassign: that is the manager', () => {
    expect(keys(planActions(makeCase(), officer))).not.toContain('reassign')
  })
})

describe('escalated and re-running cases', () => {
  it('waits for the manager: officer gets only a notice', () => {
    const plan = planActions(makeCase({ workflow: 'escalated' }), officer)
    expect(plan.actions).toEqual([])
    expect(plan.notice).toMatch(/manager/)
  })

  it('gives the manager the second-tier decision', () => {
    const plan = planActions(makeCase({ workflow: 'escalated' }), manager)
    expect(keys(plan)).toEqual(expect.arrayContaining(['second-tier-approve', 'second-tier-reject']))
    expect(primary(plan)).toBe('second-tier-approve')
  })

  it('lets the manager edit only a proposed reply, not a proposed fraud outcome', () => {
    const reply = planActions(makeCase({ workflow: 'escalated' }), manager)
    const outcome = planActions(
      makeCase({ queue: 'with_fraud_team', workflow: 'escalated', proposal: { action: 'record_outcome', outcome: 'confirmed_fraud' } }),
      manager,
    )
    expect(keys(reply)).toContain('edit-reply')
    expect(keys(outcome)).not.toContain('edit-reply')
  })

  it('locks everything while the agent re-runs', () => {
    const plan = planActions(makeCase({ workflow: 'reprocessing' }), manager)
    expect(plan.actions).toEqual([])
    expect(plan.notice).toMatch(/re-running/)
  })
})

describe('manager', () => {
  it('approves directly with no limit, and can reassign', () => {
    const plan = planActions(makeCase({ refund: '4687.10' }), manager)
    expect(primary(plan)).toBe('approve')
    expect(keys(plan)).toContain('reassign')
    expect(plan.limit).toBeNull()
  })

  it('has no buttons on a closed case', () => {
    expect(planActions(makeCase({ queue: 'approved', workflow: 'closed' }), manager).actions).toEqual([])
    expect(planActions(makeCase({ queue: 'auto_resolved' }), manager).actions).toEqual([])
  })
})

describe('fraud analyst', () => {
  const fraud = (extra = {}) => makeCase({ queue: 'with_fraud_team', ...extra })

  it('starts with Acknowledge, which sends the holding reply', () => {
    const plan = planActions(fraud(), fraudAnalyst)
    expect(keys(plan)).toEqual(['acknowledge'])
    expect(plan.notice).toMatch(/holding reply/)
  })

  it('has nothing to do on an approval case', () => {
    expect(planActions(makeCase(), fraudAnalyst).actions).toEqual([])
  })

  it('records the outcome once investigating, when within RM5,000', () => {
    const plan = planActions(fraud({ workflow: 'investigating', disputed: '5000.00' }), fraudAnalyst)
    expect(primary(plan)).toBe('record-outcome')
    expect(keys(plan)).toEqual(expect.arrayContaining(['investigate', 'escalate']))
  })

  it('must escalate when the disputed transaction is over RM5,000 (judged on the transaction, not a refund)', () => {
    const plan = planActions(fraud({ workflow: 'investigating', disputed: '5000.01' }), fraudAnalyst)
    expect(primary(plan)).toBe('escalate')
    expect(keys(plan)).not.toContain('record-outcome')
    expect(plan.limit?.subject).toMatch(/disputed transaction/)
  })

  it('must escalate a sensitive case whatever the amount', () => {
    const plan = planActions(fraud({ workflow: 'investigating', disputed: '10.00', sensitive: true }), fraudAnalyst)
    expect(primary(plan)).toBe('escalate')
  })

  it('has no buttons once the case is closed', () => {
    expect(planActions(fraud({ workflow: 'closed', sent: true }), fraudAnalyst).actions).toEqual([])
  })

  it('the manager can acknowledge and reassign too', () => {
    expect(keys(planActions(fraud(), manager))).toEqual(expect.arrayContaining(['acknowledge', 'reassign']))
  })
})
