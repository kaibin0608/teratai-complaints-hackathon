/**
 * What the agent says when you open a case: a short briefing, and the steps behind it.
 * Built only from the stored decision, so nothing here is generated or invented: it is the case's own facts, in words.
 */
import { formatMoney } from './format'
import { categoryLabel, holdReasonHelp, holdReasonLabel, outcomeLabel, routeLabel } from './labels'
import type { CaseDetail } from './types'

export interface TraceStep {
  label: string
  detail: string
  /** `check`: the step needs a person's eye (an ambiguous match, a flagged reply). */
  state: 'done' | 'check'
}

export interface Briefing {
  /** Short paragraphs, in order. */
  paragraphs: string[]
  /** The steps behind the briefing, shown on request. */
  steps: TraceStep[]
}

const LANGUAGE = { EN: 'English', MS: 'Malay' } as const

/** Why this case is not simply resolved: the hold, or else the rule that sends this kind of outcome to a person. */
function whyAPerson(detail: CaseDetail): string | null {
  const { decision } = detail
  if (!decision) return null
  if (decision.hold_reason) return `${holdReasonLabel[decision.hold_reason]}. ${holdReasonHelp[decision.hold_reason]}`
  if (decision.route === 'FRAUD_TEAM') return 'Possible fraud goes to the fraud team, and no refund is made until they have looked.'
  if (decision.route === 'HUMAN_APPROVAL') {
    return decision.outcome === 'REFUND' ? 'The refund is above the amount I may send on my own.' : 'A decline always needs a person before it reaches the customer.'
  }
  return null
}

export function buildBriefing(detail: CaseDetail): Briefing {
  const { case: c, decision, clues, match, evidence, reply } = detail

  if (c.status === 'processing') return { paragraphs: ['I’m still working on this complaint. I’ll update this page as soon as I have a decision.'], steps: [] }
  if (c.status === 'error' || !decision) {
    return { paragraphs: [`I couldn’t finish this case${c.error ? `: ${c.error}` : ''}. It needs a person to look at it.`], steps: [] }
  }

  const txn = evidence?.matched_txn ?? null
  const category = categoryLabel[decision.category]
  const checkPassed = reply?.self_check ? reply.self_check.passed : null
  const myself = c.queue === 'auto_resolved'
  // Still waiting for a person: only then does "sensitive, needs the manager" apply.
  const waiting = (c.queue === 'awaiting_approval' || c.queue === 'with_fraud_team') && c.workflow !== 'closed'

  const understood = `I read this complaint as “${category}”${clues?.amount_mentioned ? `, about ${formatMoney(clues.amount_mentioned)}` : ''}, written in ${LANGUAGE[decision.reply_language]}.`
  const found = txn
    ? `I matched transaction ${txn.txn_id} (${formatMoney(txn.amount_myr)}) and applied rule ${decision.rule_id}: ${decision.calculation.explanation}.`
    : isServiceComplaint(detail)
      ? `No transaction is involved in a service complaint. Rule ${decision.rule_id}: ${decision.calculation.explanation}.`
      : match && match.candidates.length > 1
      ? `I couldn’t tell which of ${match.candidates.length} transactions the customer means, so I did not choose one.`
      : `I couldn’t find a matching transaction. Rule ${decision.rule_id}: ${decision.calculation.explanation}.`
  const recommend =
    decision.outcome === 'REFUND'
      ? `I recommend a refund of ${formatMoney(decision.refund_amount_myr)}.`
      : `My decision is: ${outcomeLabel[decision.outcome].toLowerCase()}.`
  const person = myself ? 'It needed no one else, so I resolved it and sent the reply (simulated).' : (() => {
    const why = whyAPerson(detail)
    return why ? `It goes to ${routeLabel[decision.route].toLowerCase()}. ${why}` : `It goes to ${routeLabel[decision.route].toLowerCase()}.`
  })()
  const sensitive = c.sensitive && waiting ? `This case is marked sensitive${c.sensitive_reason ? ` (${c.sensitive_reason})` : ''}, so it needs the manager.` : null
  const check = checkPassed === null ? null : checkPassed ? 'My draft reply passed the self-check.' : 'My draft reply did not pass the self-check, so it can’t be sent as it is.'

  return {
    paragraphs: [understood, `${found} ${recommend}`, [person, sensitive, check].filter(Boolean).join(' ')].filter(Boolean),
    steps: buildSteps(detail),
  }
}

/** Service-quality complaints (staff, app, branch) never involve a transaction: no match is the expected result. */
const isServiceComplaint = (detail: CaseDetail): boolean => detail.decision?.category === 'SERVICE_QUALITY'

/** The agent's work in order, each step with what it found. */
export function buildSteps(detail: CaseDetail): TraceStep[] {
  const { complaint, decision, clues, match, evidence, reply } = detail
  if (!decision) return []
  const txn = evidence?.matched_txn ?? null
  const steps: TraceStep[] = [
    { label: 'Read the complaint', detail: `${complaint.channel}, ${LANGUAGE[decision.reply_language]}${clues?.is_mixed_language ? ' (mixed with English)' : ''}.`, state: 'done' },
    {
      label: 'Understood it',
      detail: [categoryLabel[decision.category], clues?.amount_mentioned && `${formatMoney(clues.amount_mentioned)}${clues.amount_approximate ? ' (approximate)' : ''}`, clues?.date_phrase && `“${clues.date_phrase}”`]
        .filter(Boolean)
        .join(' · '),
      state: match?.category_revised ? 'check' : 'done',
    },
    {
      label: 'Found the transaction',
      detail: txn
        ? `${txn.txn_id}, ${formatMoney(txn.amount_myr)}.`
        : isServiceComplaint(detail)
          ? 'None needed: a service complaint has no transaction.'
          : match && match.candidates.length > 1 ? `${match.candidates.length} possible matches; none chosen.` : 'No match found.',
      state: txn || isServiceComplaint(detail) ? 'done' : 'check',
    },
    { label: 'Applied the policy', detail: `${decision.rule_id}: ${decision.calculation.explanation}.`, state: 'done' },
  ]
  if (reply) {
    steps.push({ label: 'Drafted the reply', detail: `${LANGUAGE[decision.reply_language]}${reply.redraft_count > 0 ? `, redrafted ${reply.redraft_count} time${reply.redraft_count === 1 ? '' : 's'}` : ''}.`, state: 'done' })
    if (reply.self_check) {
      steps.push({
        label: 'Checked the reply',
        detail: reply.self_check.passed ? 'Every transaction ID and amount in it is in the evidence.' : 'Something in the reply is not in the evidence.',
        state: reply.self_check.passed ? 'done' : 'check',
      })
    }
  }
  steps.push({
    label: 'Chose the route',
    detail: `${routeLabel[decision.route]}${decision.hold_reason ? `, held: ${holdReasonLabel[decision.hold_reason]}` : ''}.`,
    state: decision.hold_reason ? 'check' : 'done',
  })
  return steps
}

/** Questions worth asking about this particular case, most useful first. */
export function suggestionsFor(detail: CaseDetail): string[] {
  const { decision, match } = detail
  const list: string[] = ['Why this decision?']
  if (decision?.hold_reason === 'ambiguous_match' || (match && match.candidates.length > 1)) list.push('Why not the other transactions?')
  if (decision?.hold_reason === 'self_check_failed' || (detail.reply?.self_check && !detail.reply.self_check.passed)) list.push('What failed the self-check?')
  if (decision?.outcome === 'REFUND') list.push('How was the refund worked out?')
  if (detail.case.sensitive) list.push('Why does the manager need to see this?')
  if (decision?.route === 'FRAUD_TEAM') list.push('What should I check before acknowledging?')
  list.push('What does the evidence show?', 'Can I approve this myself?', 'Which policy applies?')
  return [...new Set(list)].slice(0, 4)
}
