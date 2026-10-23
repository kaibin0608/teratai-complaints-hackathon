import { Card } from '@/components/shared/Card'
import type { PolicyParameter } from '@/lib/policy'
import { PolicySection } from './PolicySection'
import { PolicyTable, type Column } from './PolicyTable'

const COLUMNS: readonly Column<PolicyParameter>[] = [
  { head: 'Setting', render: (p) => p.label },
  { head: 'Value', render: (p) => (p.value ? <span className="whitespace-nowrap tabular-nums">{p.value}</span> : <span className="text-secondary">See rule</span>) },
  { head: 'What it means', render: (p) => p.meaning },
]

/** The limits, ages and windows, plus the routing and reply-language rules. */
export function ThresholdsSection({ parameters }: { parameters: readonly PolicyParameter[] }) {
  return (
    <PolicySection id="thresholds" title="Limits and thresholds" description="The numbers the rules above use, and the two rules that decide who handles a case and in which language.">
      <Card title="Policy parameters">
        <PolicyTable columns={COLUMNS} rows={parameters} rowKey={(p) => p.key} />
      </Card>
    </PolicySection>
  )
}
