import { Card } from '@/components/shared/Card'
import { CategoryTag } from '@/components/shared/CategoryTag'
import { DetailList } from '@/components/shared/DetailList'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import type { CategoryRule } from '@/lib/policy'
import { PolicySection } from './PolicySection'

/** One card per complaint category: what it covers, how the transaction is found, and the decision rule. */
export function RulesSection({ rules }: { rules: readonly CategoryRule[] }) {
  return (
    <PolicySection
      id="rules"
      title="Decision rules"
      description="What the agent decides for each kind of complaint. Code applies these exactly; the language model never decides money."
    >
      <div className="grid gap-section lg:grid-cols-2">
        {rules.map((rule) => (
          <Card
            key={rule.category}
            title={<CategoryTag category={rule.category} />}
            aside={
              <span className="flex items-center gap-1.5 text-xs text-secondary">
                Base priority <PriorityBadge priority={rule.basePriority} />
              </span>
            }
          >
            <DetailList
              items={[
                { label: 'Covers', value: rule.covers },
                { label: 'Finding the transaction', value: rule.howToFind },
                { label: 'Decision', value: rule.decision },
              ]}
            />
          </Card>
        ))}
      </div>
    </PolicySection>
  )
}
