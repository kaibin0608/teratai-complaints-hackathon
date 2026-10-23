import { Card } from '@/components/shared/Card'
import { DetailList } from '@/components/shared/DetailList'
import { formatMs } from '@/lib/format'
import type { CaseDetail, LLMUsage } from '@/lib/types'

/** Cost and speed per complaint (judged under Engineering): what it cost, how long, and which models. */
export function UsageCard({ detail }: { detail: CaseDetail }) {
  const { usage, runs } = detail
  if (!usage) return null
  const calls: { step: string; call: LLMUsage }[] = [
    { step: 'Understand', call: usage.extract },
    ...usage.draft.map((call, index) => ({ step: usage.draft.length > 1 ? `Draft ${index + 1}` : 'Draft', call })),
  ]

  return (
    <Card title="Cost and speed">
      <DetailList
        items={[
          { label: 'Cost', value: <span className="tabular-nums">RM{usage.cost_myr}</span> },
          { label: 'Time', value: <span className="tabular-nums">{formatMs(usage.latency_ms)}</span> },
          { label: 'Agent runs', value: runs.length > 1 ? `${runs.length} (one after a send back)` : '1' },
          { label: 'Policy', value: usage.policy_version },
          { label: 'Prompt / schema', value: `${usage.prompt_version} · ${usage.schema_version}` },
        ]}
      />
      <ul className="mt-3 divide-y divide-neutral-100 rounded-control border border-subtle text-sm">
        {calls.map(({ step, call }) => (
          <li key={step} className="flex flex-wrap items-baseline justify-between gap-x-3 px-3 py-2">
            <span className="text-primary">
              {step} <span className="text-secondary">· {call.provider}:{call.model}</span>
            </span>
            <span className="text-xs text-secondary tabular-nums">
              {call.tokens_in + call.tokens_out} tokens · RM{call.cost_myr} · {formatMs(call.latency_ms)}
              {call.cached && ' · cached'}
              {call.retries > 0 && ` · ${call.retries} retr${call.retries === 1 ? 'y' : 'ies'}`}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  )
}
