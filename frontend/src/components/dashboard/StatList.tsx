import type { ReactNode } from 'react'
import { Card } from '@/components/shared/Card'

export interface Stat {
  label: string
  /** The number; shown large in Geist. */
  value: ReactNode
  /** One muted line under the label saying what the number means. */
  detail?: ReactNode
}

/** A quiet list of numbers: label and meaning on the left, the value on the right. Denser and calmer than a grid of tiles. */
export function StatList({ title, stats }: { title: string; stats: readonly Stat[] }) {
  return (
    <Card title={title}>
      <dl className="-my-2 divide-y divide-neutral-100">
        {stats.map((stat) => (
          <div key={stat.label} className="flex items-baseline justify-between gap-4 py-2.5">
            <div className="min-w-0">
              <dt className="text-sm text-primary">{stat.label}</dt>
              {stat.detail && <dd className="mt-0.5 text-xs text-secondary">{stat.detail}</dd>}
            </div>
            <dd className="shrink-0 font-display text-xl font-semibold text-primary tabular-nums">{stat.value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  )
}
