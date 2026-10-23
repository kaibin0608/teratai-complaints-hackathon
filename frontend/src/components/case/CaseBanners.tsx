import { CircleArrowUp, CirclePause, HandHeart, LoaderCircle, TriangleAlert } from 'lucide-react'
import { Banner } from '@/components/shared/Banner'
import { awaitsFirstTier } from '@/lib/case'
import { formatIsoTime } from '@/lib/format'
import { holdReasonHelp, holdReasonLabel, routeLabel } from '@/lib/labels'
import type { CaseDetail } from '@/lib/types'

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
    c.workflow === 'escalated' && c.escalation && (
      <Banner
        key="escalated"
        tone="error"
        icon={CircleArrowUp}
        title={`Escalated to the manager by ${c.escalation.by} · ${formatIsoTime(c.escalation.at)}`}
      >
        {c.escalation.reason}
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
