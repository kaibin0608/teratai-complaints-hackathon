import { CircleArrowUp, CirclePause, HandHeart, LoaderCircle, Repeat2, TriangleAlert } from 'lucide-react'
import { Banner } from '@/components/shared/Banner'
import { awaitsFirstTier } from '@/lib/case'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { fraudOutcomeLabel, holdReasonHelp, holdReasonLabel, outcomeLabel, routeLabel } from '@/lib/labels'
import type { CaseDetail, Escalation } from '@/lib/types'

/** What the manager is being asked to approve. */
function describeProposal(proposal: Escalation['proposal']): string {
  if (proposal.action === 'record_outcome') return `record the fraud outcome “${fraudOutcomeLabel[proposal.outcome]}”.`
  const reply = proposal.edited ? 'the officer’s edited reply' : 'the agent’s reply'
  return `send ${reply} and any refund (self-check ${proposal.self_check}).`
}

/** Why this case needs extra care, most urgent first. Renders nothing for a routine case. */
export function CaseBanners({ detail }: { detail: CaseDetail }) {
  const { case: c, decision } = detail
  const movedByHold = decision && decision.policy_route !== decision.route

  const banners = [
    c.status === 'error' && (
      <Banner key="error" tone="error" icon={TriangleAlert} title="The agent could not finish this case">
        {c.error}
      </Banner>
    ),
    (c.status === 'processing' || c.workflow === 'reprocessing') && (
      <Banner key="processing" tone="info" icon={LoaderCircle} title="The agent is working on this case">
        {c.workflow === 'reprocessing' ? 'Re-running after a send back. ' : ''}This page updates when it finishes.
      </Banner>
    ),
    detail.autonomous && c.current_run_id !== c.autonomous_run_id && (
      <Banner key="rerun" tone="info" icon={Repeat2} title="Showing the agent's re-run after a send back">
        Its first decision (the one that is scored) was {outcomeLabel[detail.autonomous.outcome]}
        {detail.autonomous.outcome === 'REFUND' && ` ${formatMoney(detail.autonomous.refund_amount_myr)}`}
        {` → ${routeLabel[detail.autonomous.route]}`}. The re-run always waits for a person.
      </Banner>
    ),
    c.workflow === 'escalated' && c.escalation && (
      <Banner
        key="escalated"
        tone="error"
        icon={CircleArrowUp}
        title={`Escalated to the manager by ${c.escalation.by} · ${formatIsoTime(c.escalation.at)}`}
      >
        {c.escalation.reason}
        <br />
        <span className="font-medium">Proposal: </span>
        {describeProposal(c.escalation.proposal)}
      </Banner>
    ),
    decision?.hold_reason && (
      <Banner key="held" tone="warning" icon={CirclePause} title={`Held for review: ${holdReasonLabel[decision.hold_reason]}`}>
        {holdReasonHelp[decision.hold_reason]}
        {movedByHold && ` Policy route was ${routeLabel[decision.policy_route]}; the hold moved it to ${routeLabel[decision.route]}.`}
      </Banner>
    ),
    // Sensitive matters while a first-tier user still has to act; once escalated, the escalation banner says it.
    c.sensitive && awaitsFirstTier(detail) && (
      <Banner key="sensitive" tone="aubergine" icon={HandHeart} title="Sensitive case">
        {(c.sensitive_reason ?? 'Flagged sensitive').replace(/\.?$/, '.')} Approval must be escalated to a manager.
      </Banner>
    ),
  ].filter(Boolean)

  if (banners.length === 0) return null
  return <div className="flex flex-col gap-2">{banners}</div>
}
