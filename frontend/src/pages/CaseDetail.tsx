import { LoaderCircle } from 'lucide-react'
import { useParams } from 'react-router'
import { CaseActions } from '@/components/case/actions/CaseActions'
import { AgentVsHumanCard } from '@/components/case/AgentVsHumanCard'
import { CaseBanners } from '@/components/case/CaseBanners'
import { CaseLoadError } from '@/components/case/CaseLoadError'
import { CaseSla } from '@/components/case/CaseSla'
import { ComplaintCard } from '@/components/case/ComplaintCard'
import { CustomerCard } from '@/components/case/CustomerCard'
import { DecisionCard } from '@/components/case/DecisionCard'
import { EvidenceCard } from '@/components/case/EvidenceCard'
import { MatchCard } from '@/components/case/MatchCard'
import { ReplyCard } from '@/components/case/ReplyCard'
import { TimelineCard } from '@/components/case/TimelineCard'
import { UsageCard } from '@/components/case/UsageCard'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/shared/Badge'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { routeLabel } from '@/lib/labels'

/** Shared case view; adapts to the signed-in role (PLAN.md §3, FRONTEND_BUILD.md B2). */
export function CaseDetail() {
  const { complaintId = '' } = useParams()
  const result = useCaseDetail(complaintId)

  if (result.status === 'loading') {
    return (
      <Page title={complaintId}>
        <StatusMessage busy icon={LoaderCircle} title="Loading case…" />
      </Page>
    )
  }
  if (result.status === 'error') {
    return (
      <Page title={complaintId}>
        <CaseLoadError error={result.error} onRetry={result.reload} />
      </Page>
    )
  }

  const detail = result.data
  const { decision } = detail
  return (
    <Page
      title={detail.case.complaint_id}
      meta={
        <>
          {decision && <CategoryBadge category={decision.category} />}
          {decision && <PriorityBadge priority={decision.priority} />}
          <QueueBadge queue={detail.case.queue} />
          {detail.case.workflow && <WorkflowBadge workflow={detail.case.workflow} />}
          {decision && <Badge tone="tag">{routeLabel[decision.route]}</Badge>}
        </>
      }
      actions={<CaseSla detail={detail} />}
      footer={<CaseActions detail={detail} onChanged={result.reload} />}
    >
      <div className="flex flex-col gap-section">
        <CaseBanners detail={detail} />
        <div className="grid items-start gap-section lg:grid-cols-2">
          <div className="flex flex-col gap-section">
            <ComplaintCard detail={detail} />
            <CustomerCard detail={detail} />
            <EvidenceCard detail={detail} />
            <MatchCard detail={detail} />
          </div>
          <div className="flex flex-col gap-section">
            <DecisionCard detail={detail} />
            <ReplyCard detail={detail} />
            <AgentVsHumanCard detail={detail} />
            <UsageCard detail={detail} />
          </div>
        </div>
        <TimelineCard detail={detail} />
      </div>
    </Page>
  )
}
