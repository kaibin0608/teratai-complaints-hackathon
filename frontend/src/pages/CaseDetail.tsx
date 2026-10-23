import { LoaderCircle } from 'lucide-react'
import { useParams } from 'react-router'
import { AgentPane } from '@/components/case/agent/AgentPane'
import { CaseActions } from '@/components/case/actions/CaseActions'
import { CaseTabs } from '@/components/case/CaseTabs'
import { CaseBanners } from '@/components/case/CaseBanners'
import { CaseLoadError } from '@/components/case/CaseLoadError'
import { CaseSla } from '@/components/case/CaseSla'
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
      fill
    >
      <div className="flex flex-col gap-section xl:h-full">
        <CaseBanners detail={detail} />
        {/* Details left, the agent on the right. Stacked on narrower screens, the agent comes first. */}
        <div className="grid items-start gap-section xl:min-h-0 xl:flex-1 xl:grid-cols-[minmax(0,1fr)_33rem]">
          <div className="min-w-0 xl:order-1 xl:h-full xl:min-h-0">
            <CaseTabs key={`tabs-${detail.case.complaint_id}`} detail={detail} />
          </div>
          <div className="-order-1 min-w-0 xl:order-2 xl:h-full xl:min-h-0">
            <AgentPane key={detail.case.complaint_id} detail={detail} />
          </div>
        </div>
      </div>
    </Page>
  )
}
