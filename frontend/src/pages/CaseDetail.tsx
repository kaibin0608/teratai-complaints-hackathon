import { LoaderCircle } from 'lucide-react'
import { useParams } from 'react-router'
import { CaseActions } from '@/components/case/actions/CaseActions'
import { AgentVsHumanCard } from '@/components/case/AgentVsHumanCard'
import { CaseBanners } from '@/components/case/CaseBanners'
import { CaseLoadError } from '@/components/case/CaseLoadError'
import { CaseSla } from '@/components/case/CaseSla'
import { CluesCard } from '@/components/case/CluesCard'
import { ComplaintCard } from '@/components/case/ComplaintCard'
import { CustomerCard } from '@/components/case/CustomerCard'
import { DecisionCard } from '@/components/case/DecisionCard'
import { EvidenceCard } from '@/components/case/EvidenceCard'
import { FraudOutcomeCard } from '@/components/case/FraudOutcomeCard'
import { MatchCard } from '@/components/case/MatchCard'
import { ReplyCard } from '@/components/case/ReplyCard'
import { RunsCard } from '@/components/case/RunsCard'
import { TimelineCard } from '@/components/case/TimelineCard'
import { UsageCard } from '@/components/case/UsageCard'
import { NoticeBanner } from '@/components/layout/NoticeBanner'
import { Page } from '@/components/layout/Page'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { useAuth } from '@/hooks/useAuth'
import { homeFor, paths } from '@/lib/paths'
import type { CaseDetail as CaseDetailData } from '@/lib/types'

/** "Closed" adds nothing once the queue already says Approved or Rejected. */
const showWorkflow = ({ case: c }: CaseDetailData) => !(c.workflow === 'closed' && (c.queue === 'approved' || c.queue === 'rejected'))

/** Shared case view; adapts to the signed-in role (PLAN.md §3, FRONTEND_BUILD.md B2). */
export function CaseDetail() {
  const { complaintId = '' } = useParams()
  const auth = useAuth()
  const result = useCaseDetail(complaintId)
  const back = {
    to: auth.status === 'signed_in' && auth.user.role !== 'manager' ? homeFor[auth.user.role] : paths.cases,
    label: 'Back to the queue',
  }

  if (result.status === 'loading') {
    return (
      <Page title={complaintId} back={back}>
        <StatusMessage busy icon={LoaderCircle} title="Loading case…" />
      </Page>
    )
  }
  if (result.status === 'error') {
    return (
      <Page title={complaintId} back={back}>
        <CaseLoadError error={result.error} onRetry={result.reload} />
      </Page>
    )
  }

  const detail = result.data
  const { decision } = detail
  return (
    <Page
      title={detail.case.complaint_id}
      back={back}
      meta={
        <>
          {decision && <CategoryBadge category={decision.category} />}
          {decision && <PriorityBadge priority={decision.priority} />}
          <QueueBadge queue={detail.case.queue} />
          {showWorkflow(detail) && detail.case.workflow && <WorkflowBadge workflow={detail.case.workflow} />}
        </>
      }
      actions={<CaseSla detail={detail} />}
      footer={<CaseActions detail={detail} onChanged={result.reload} />}
    >
      <div className="flex flex-col gap-section">
        <NoticeBanner />
        <CaseBanners detail={detail} />
        <div className="grid items-start gap-section lg:grid-cols-2">
          <div className="flex flex-col gap-section">
            <ComplaintCard detail={detail} />
            <CluesCard detail={detail} />
            <CustomerCard detail={detail} />
            <EvidenceCard detail={detail} />
            <MatchCard detail={detail} />
          </div>
          <div className="flex flex-col gap-section">
            <DecisionCard detail={detail} />
            <FraudOutcomeCard detail={detail} />
            <ReplyCard detail={detail} />
            <AgentVsHumanCard detail={detail} />
            <RunsCard detail={detail} />
            <UsageCard detail={detail} />
          </div>
        </div>
        <TimelineCard detail={detail} />
      </div>
    </Page>
  )
}
