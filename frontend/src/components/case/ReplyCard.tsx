import { Badge } from '@/components/shared/Badge'
import { Card } from '@/components/shared/Card'
import { SelfCheckBadge } from '@/components/shared/SelfCheckBadge'
import { formatIsoTime, formatMoney } from '@/lib/format'
import { highlightReply } from '@/lib/replyCheck'
import type { CaseDetail } from '@/lib/types'
import { useNameOf } from '@/hooks/useNameOf'

/** The drafted reply with its self-check. Any ID or amount not in the evidence is marked in red. */
export function ReplyCard({ detail }: { detail: CaseDetail }) {
  const nameOf = useNameOf()
  const { reply, evidence, draft_reply: draft } = detail
  if (!reply) return null
  const check = reply.self_check
  const allowedIds = evidence?.allowed_txn_ids ?? []
  const allowedAmounts = evidence?.allowed_amounts ?? []

  return (
    <Card title="Reply" aside={check && <SelfCheckBadge result={check.passed ? 'passed' : 'flagged'} />}>
      <ReplyText text={reply.text} allowedIds={allowedIds} allowedAmounts={allowedAmounts} />

      {check && !check.passed && <Problems problems={check.problems} />}

      <p className="mt-2 text-xs text-secondary">
        {reply.redraft_count > 0
          ? `Redrafted ${reply.redraft_count} time${reply.redraft_count === 1 ? '' : 's'} after the self-check.`
          : 'First draft.'}{' '}
        The reply may only mention: {allowedFacts(allowedIds, allowedAmounts)}.
      </p>

      {draft && (
        <div className="mt-4 border-t border-subtle pt-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Edited draft awaiting approval</h3>
            <SelfCheckBadge result={draft.self_check} />
          </div>
          <ReplyText text={draft.text} allowedIds={allowedIds} allowedAmounts={allowedAmounts} />
          {draft.problems.length > 0 && <Problems problems={draft.problems} />}
          <p className="mt-2 text-xs text-secondary">
            Edited by {nameOf(draft.by)} · {formatIsoTime(draft.at)}
          </p>
        </div>
      )}
    </Card>
  )
}

/** "TXN-0151125 · RM1,500.00 · RM0.00": each fact once, amounts formatted. */
function allowedFacts(ids: readonly string[], amounts: readonly string[]): string {
  const facts = [...new Set(ids), ...new Set(amounts.map(formatMoney))]
  return facts.length > 0 ? facts.join(' · ') : 'nothing'
}

function ReplyText({ text, allowedIds, allowedAmounts }: { text: string; allowedIds: string[]; allowedAmounts: string[] }) {
  return (
    <p className="rounded-control bg-subtle px-3 py-2.5 text-sm leading-relaxed whitespace-pre-line text-body">
      {highlightReply(text, allowedIds, allowedAmounts).map((segment, index) =>
        segment.flagged ? (
          <mark
            key={index}
            title="Not in the evidence"
            className="rounded-badge bg-error-100 px-0.5 font-medium text-error-800 underline decoration-error-500 decoration-wavy"
          >
            {segment.text}
          </mark>
        ) : (
          segment.text
        ),
      )}
    </p>
  )
}

function Problems({ problems }: { problems: readonly string[] }) {
  return (
    <ul className="mt-2 flex flex-col gap-1">
      {problems.map((problem) => (
        <li key={problem}>
          <Badge tone="error">{problem}</Badge>
        </li>
      ))}
    </ul>
  )
}
