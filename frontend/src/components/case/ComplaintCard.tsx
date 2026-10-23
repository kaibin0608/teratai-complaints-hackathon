import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatIsoTime } from '@/lib/format'
import type { CaseDetail } from '@/lib/types'

/** The customer's words, as received. */
export function ComplaintCard({ detail }: { detail: CaseDetail }) {
  const { complaint, clues } = detail
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
    </Card>
  )
}
