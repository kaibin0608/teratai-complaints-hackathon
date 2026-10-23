import { Lock } from 'lucide-react'
import { useState } from 'react'
import { Page } from '@/components/layout/Page'
import { ApprovalSection } from '@/components/policy/ApprovalSection'
import { FeesAndSlaSection } from '@/components/policy/FeesAndSlaSection'
import { RulesSection } from '@/components/policy/RulesSection'
import { ThresholdsSection } from '@/components/policy/ThresholdsSection'
import { Badge } from '@/components/shared/Badge'
import { Tabs } from '@/components/shared/Tabs'
import { loadPolicy } from '@/lib/policy'

const POLICY = loadPolicy()

const TABS = [
  { value: 'rules', label: 'Decision rules' },
  { value: 'thresholds', label: 'Limits and thresholds' },
  { value: 'fees', label: 'Fees and service levels' },
  { value: 'approval', label: 'Approval and escalation' },
] as const

type Tab = (typeof TABS)[number]['value']

/** Manager: the bank's rules, for reference. They are fixed, so there is nothing to edit (PLAN.md: policy editing is out of scope). */
export function Policy() {
  const [tab, setTab] = useState<Tab>('rules')
  return (
    <Page
      title="Policy"
      meta={
        <Badge tone="neutral" icon={Lock}>
          Read-only
        </Badge>
      }
    >
      <div className="flex flex-col gap-section">
        <p className="text-sm text-secondary">
          Fixed by the bank. These are the rules the agent applies to every complaint, read straight from the bank&apos;s policy files, so what you see is what it uses.
        </p>
        <Tabs label="Policy sections" items={TABS} value={tab} onChange={setTab} />
        {tab === 'rules' && <RulesSection rules={POLICY.rules} />}
        {tab === 'thresholds' && <ThresholdsSection parameters={POLICY.parameters} />}
        {tab === 'fees' && <FeesAndSlaSection fees={POLICY.fees} sla={POLICY.sla} />}
        {tab === 'approval' && <ApprovalSection policy={POLICY} />}
      </div>
    </Page>
  )
}
