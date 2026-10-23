import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { DetailList } from '@/components/shared/DetailList'
import { formatIsoTime } from '@/lib/format'
import type { CaseDetail } from '@/lib/types'

/** The customer's words, as received, and any second problem the issues check found in them. */
export function ComplaintCard({ detail }: { detail: CaseDetail }) {
  const { complaint, clues } = detail
  const otherIssues = detail.other_issues ?? []
  const staffNote = complaint.channel === 'Call centre note'
  const language = clues ? (clues.is_mixed_language ? 'Mixed EN/MS' : clues.language) : null

  return (
    <Card
      title="Complaint"
      aside={
        <div className="flex gap-1">
          {staffNote && <Badge tone="tag">Staff note</Badge>}
          {language && <Badge tone="tag">{language}</Badge>}
        </div>
      }
    >
      <DetailList
        items={[
          { label: 'Channel', value: complaint.channel },
          { label: 'Received', value: <span className="tabular-nums">{formatIsoTime(complaint.received_at)}</span> },
          { label: 'Subject', value: complaint.subject },
        ]}
      />
      <p className="mt-3 rounded-control bg-subtle px-3 py-2.5 text-sm leading-relaxed whitespace-pre-line text-body">
        {complaint.text}
      </p>
      {otherIssues.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          <p className="text-xs font-medium text-secondary">Also raised in this complaint</p>
          {otherIssues.map((issue) => (
            <div key={issue.category} className="flex flex-col items-start gap-1.5 rounded-control bg-warning-50 px-3 py-2.5">
              <CategoryBadge category={issue.category} />
              <q className="text-sm leading-relaxed text-body">{issue.quote}</q>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
