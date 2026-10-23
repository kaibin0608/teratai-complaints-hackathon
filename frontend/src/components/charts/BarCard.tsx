import { formatPercent } from '@/lib/format'
import { ChartCard } from './ChartCard'
import { BAR_COLOURS } from './chartTones'

export interface BarItem {
  label: string
  value: number
}

interface BarCardProps {
  title: string
  subtitle?: string
  items: readonly BarItem[]
  /** Largest first (default). Turn off for an ordered scale such as P1 → P3. */
  sort?: boolean
  /** Noun for the table's count column. */
  unit?: string
}

/**
 * "How many of each?" as horizontal bars, one colour per value (the label still names it). The value sits at the bar tip.
 * Marks follow the data-viz spec: thin bars, a 4px rounded data end, square on the baseline.
 */
export function BarCard({ title, subtitle, items, sort = true, unit = 'Cases' }: BarCardProps) {
  // Each value keeps the colour of its place in the given order, whatever the sort.
  const coloured = items.map((item, index) => ({ ...item, colour: BAR_COLOURS[index % BAR_COLOURS.length]! }))
  const rows = sort ? [...coloured].sort((a, b) => b.value - a.value) : coloured
  const total = rows.reduce((sum, row) => sum + row.value, 0)
  const max = Math.max(1, ...rows.map((row) => row.value))
  const share = (value: number) => (total === 0 ? null : value / total)

  return (
    <ChartCard
      title={title}
      subtitle={subtitle}
      table={{
        head: ['', unit, 'Share'],
        rows: rows.map((row) => [row.label, row.value, formatPercent(share(row.value))]),
      }}
      chart={
        total === 0 ? (
          <p className="py-6 text-center text-sm text-secondary">Nothing yet.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {rows.map((row) => (
              <li
                key={row.label}
                title={`${row.label}: ${row.value} (${formatPercent(share(row.value))})`}
                className="grid grid-cols-[minmax(7rem,11rem)_1fr] items-center gap-3 rounded-control px-1 py-0.5 hover:bg-subtle"
              >
                <span className="text-sm leading-tight text-body">{row.label}</span>
                <span className="flex items-center gap-2">
                  <span aria-hidden className="relative h-2.5 flex-1 rounded-[4px] bg-neutral-50">
                    {row.value > 0 && <span className={`absolute inset-y-0 left-0 rounded-[4px] ${row.colour}`} style={{ width: `${(row.value / max) * 100}%`, minWidth: 4 }} />}
                  </span>
                  <span className="text-xs whitespace-nowrap text-primary tabular-nums">
                    {row.value}
                    <span className="ml-1 text-secondary">{formatPercent(share(row.value))}</span>
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )
      }
    />
  )
}
