import type { ReactNode } from 'react'
import { Page } from '@/components/layout/Page'
import { Button } from '@/components/shared/Button'
import { CategoryBadge } from '@/components/shared/CategoryBadge'
import { HoldBadge } from '@/components/shared/HoldBadge'
import { PriorityBadge } from '@/components/shared/PriorityBadge'
import { SimulatedBadge } from '@/components/shared/SimulatedBadge'
import { SLATimer } from '@/components/shared/SLATimer'
import { QueueBadge } from '@/components/shared/QueueBadge'
import { VulnerableBadge } from '@/components/shared/VulnerableBadge'
import { WorkflowBadge } from '@/components/shared/WorkflowBadge'
import { demoNowMs, msToMyt } from '@/lib/clock'
import { formatMoney } from '@/lib/format'
import { CATEGORIES, HOLD_REASONS, PRIORITIES, QUEUES, WORKFLOWS } from '@/lib/types'

const HOUR = 3_600_000

/** Dev-only living style guide (route registered only in development). */
export function UiKit() {
  const now = demoNowMs()
  const at = (offsetMs: number) => msToMyt(now + offsetMs)

  return (
    <Page title="UI kit" actions={<Button variant="primary">Primary action</Button>}>
      <div className="flex max-w-4xl flex-col gap-section">
        <Section title="Typography">
          <p className="font-display text-3xl font-semibold text-primary tabular-nums">{formatMoney('48210.5')}</p>
          <p className="text-sm text-body">Inter body text for tables, labels and charts. TXN-0088211 · RM1,383.20</p>
          <p className="text-xs text-secondary">Secondary meta text · 30-09-2026 10:15:00</p>
        </Section>

        <Section title="Buttons">
          <Button variant="primary">Approve</Button>
          <Button variant="secondary">Edit reply</Button>
          <Button variant="ghost">View evidence</Button>
          <Button variant="danger">Reject</Button>
          <Button variant="primary" disabled>
            Disabled
          </Button>
        </Section>

        <Section title="Priority">
          {PRIORITIES.map((p) => (
            <PriorityBadge key={p} priority={p} />
          ))}
        </Section>

        <Section title="Queue">
          {QUEUES.map((q) => (
            <QueueBadge key={q} queue={q} />
          ))}
        </Section>

        <Section title="Workflow (ops platform)">
          {WORKFLOWS.map((w) => (
            <WorkflowBadge key={w} workflow={w} />
          ))}
        </Section>

        <Section title="Category">
          {CATEGORIES.map((c) => (
            <CategoryBadge key={c} category={c} />
          ))}
        </Section>

        <Section title="Hold reasons">
          {HOLD_REASONS.map((r) => (
            <HoldBadge key={r} reason={r} />
          ))}
        </Section>

        <Section title="Tags">
          <VulnerableBadge />
          <SimulatedBadge />
        </Section>

        <Section title="SLA timers (live, demo clock)">
          <SLATimer label="Ack" start={at(-1 * HOUR)} due={at(20 * HOUR)} />
          <SLATimer label="Ack" start={at(-10 * HOUR)} due={at(2 * HOUR)} />
          <SLATimer label="Resolve" start={at(-3 * 24 * HOUR)} due={at(-5 * HOUR)} />
        </Section>
      </div>
    </Page>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </section>
  )
}
