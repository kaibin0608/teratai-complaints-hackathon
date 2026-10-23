import { Lock } from 'lucide-react'
import { Page } from '@/components/layout/Page'
import { ApprovalSection } from '@/components/policy/ApprovalSection'
import { FeesAndSlaSection } from '@/components/policy/FeesAndSlaSection'
import { RulesSection } from '@/components/policy/RulesSection'
import { ThresholdsSection } from '@/components/policy/ThresholdsSection'
import { Badge } from '@/components/shared/Badge'
import { Banner } from '@/components/shared/Banner'
import { loadPolicy } from '@/lib/policy'

const POLICY = loadPolicy()

const CONTENTS = [
  { id: 'rules', label: 'Decision rules' },
  { id: 'thresholds', label: 'Limits and thresholds' },
  { id: 'fees', label: 'Fee schedule' },
  { id: 'sla', label: 'Service levels' },
  { id: 'approval', label: 'Approval and escalation' },
] as const

/** Manager: the bank's rules, for reference. They are fixed, so there is nothing to edit (PLAN.md: policy editing is out of scope). */
export function Policy() {
  return (
    <Page
      title="Policy"
      meta={
        <Badge tone="neutral" icon={Lock}>
          Read-only
        </Badge>
      }
    >
      <div className="flex max-w-5xl flex-col gap-section">
        <Banner tone="info" icon={Lock} title="Fixed by the bank">
          These are the rules the agent applies to every complaint. They cannot be changed here or anywhere in the app. They are read from the bank&apos;s policy files, so what you see is
          what the agent uses.
        </Banner>

        <nav aria-label="On this page" className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {CONTENTS.map(({ id, label }) => (
            <a key={id} href={`#${id}`} className="font-medium text-link hover:text-link-hover">
              {label}
            </a>
          ))}
        </nav>

        <RulesSection rules={POLICY.rules} />
        <ThresholdsSection parameters={POLICY.parameters} />
        <FeesAndSlaSection fees={POLICY.fees} sla={POLICY.sla} />
        <ApprovalSection policy={POLICY} />
      </div>
    </Page>
  )
}
