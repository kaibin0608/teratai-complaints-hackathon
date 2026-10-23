import { LoaderCircle } from 'lucide-react'
import { useParams } from 'react-router'
import { CaseBanners } from '@/components/case/CaseBanners'
import { CaseLoadError } from '@/components/case/CaseLoadError'
import { CaseSla } from '@/components/case/CaseSla'
import { Page } from '@/components/layout/Page'
import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { useCaseDetail } from '@/hooks/useCaseDetail'
import { routeLabel } from '@/lib/labels'

/** Shared case view; adapts to the signed-in role (PLAN.md §3, FRONTEND_BUILD.md screen 3). */
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
    >
      <div className="flex flex-col gap-section">
        <CaseBanners detail={detail} />
        <div className="grid items-start gap-section lg:grid-cols-2">
          <div className="flex flex-col gap-section">
            <Card title="Complaint">
              <Pending piece="9b" />
            </Card>
            <Card title="Customer">
              <Pending piece="9b" />
            </Card>
            <Card title="Evidence">
              <Pending piece="9b" />
            </Card>
          </div>
          <div className="flex flex-col gap-section">
            <Card title="Decision">
              <Pending piece="9c" />
            </Card>
            <Card title="Reply">
              <Pending piece="9c" />
            </Card>
          </div>
        </div>
        <Card title="Timeline">
          <Pending piece="9d" />
        </Card>
      </div>
    </Page>
  )
}

/** Placeholder until the card's piece is built. */
function Pending({ piece }: { piece: string }) {
  return <p className="text-sm text-secondary">Built in piece {piece}.</p>
}
