import { useState } from 'react'
import { Tabs } from '@/components/shared/Tabs'
import type { CaseDetail } from '@/lib/types'
import { AgentVsHumanCard } from './AgentVsHumanCard'
import { CluesCard } from './CluesCard'
import { ComplaintCard } from './ComplaintCard'
import { CustomerCard } from './CustomerCard'
import { DecisionCard } from './DecisionCard'
import { EvidenceCard } from './EvidenceCard'
import { FraudOutcomeCard } from './FraudOutcomeCard'
import { MatchCard } from './MatchCard'
import { ReplyCard } from './ReplyCard'
import { RunsCard } from './RunsCard'
import { TimelineCard } from './TimelineCard'
import { UsageCard } from './UsageCard'

const TABS = [
  { value: 'case', label: 'Case' },
  { value: 'decision', label: 'Decision' },
  { value: 'evidence', label: 'Evidence' },
  { value: 'reply', label: 'Reply' },
  { value: 'timeline', label: 'Timeline' },
  { value: 'run', label: 'Agent run' },
] as const

type Tab = (typeof TABS)[number]['value']

/**
 * Everything the agent's briefing refers to, one tab each, so the conversation keeps the centre of the page and the
 * facts a person verifies before acting are a click away.
 */
export function CaseTabs({ detail }: { detail: CaseDetail }) {
  const [tab, setTab] = useState<Tab>('case')
  return (
    <aside aria-label="Case details" className="flex min-w-0 flex-col gap-3 xl:h-full xl:min-h-0">
      <div className="shrink-0 overflow-x-auto">
        <Tabs label="Case details" items={TABS} value={tab} onChange={setTab} />
      </div>
      <div className="flex flex-col gap-section xl:min-h-0 xl:flex-1 xl:overflow-y-auto xl:pr-1">
        {tab === 'case' && (
          <>
            <ComplaintCard detail={detail} />
            <CustomerCard detail={detail} />
            <CluesCard detail={detail} />
          </>
        )}
        {tab === 'decision' && (
          <>
            <DecisionCard detail={detail} />
            <MatchCard detail={detail} />
            <FraudOutcomeCard detail={detail} />
            <AgentVsHumanCard detail={detail} />
          </>
        )}
        {tab === 'evidence' && <EvidenceCard detail={detail} />}
        {tab === 'reply' && <ReplyCard detail={detail} />}
        {tab === 'timeline' && <TimelineCard detail={detail} />}
        {tab === 'run' && (
          <>
            <RunsCard detail={detail} />
            <UsageCard detail={detail} />
          </>
        )}
      </div>
    </aside>
  )
}
