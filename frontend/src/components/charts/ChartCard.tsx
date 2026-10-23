import { useState, type ReactNode } from 'react'
import { Card } from '@/components/shared/Card'
import { cx } from '@/lib/cx'

export interface ChartTable {
  head: readonly string[]
  rows: readonly (readonly (string | number)[])[]
}

interface ChartCardProps {
  title: string
  /** One line saying what is plotted and over what. */
  subtitle?: string
  chart: ReactNode
  /** The same numbers as text: always available, for screen readers and exact values. */
  table: ChartTable
}

/** A card holding one chart, with a Chart | Table switch so the exact numbers are never locked inside a picture. */
export function ChartCard({ title, subtitle, chart, table }: ChartCardProps) {
  const [view, setView] = useState<'chart' | 'table'>('chart')
  return (
    <Card
      title={title}
      aside={
        <div role="group" aria-label={`${title} view`} className="flex rounded-control border border-default p-0.5">
          {(['chart', 'table'] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              onClick={() => setView(value)}
              className={cx(
                'rounded-control px-2 py-0.5 text-xs font-medium capitalize transition-colors',
                view === value ? 'bg-neutral-100 text-primary' : 'text-secondary hover:text-primary',
              )}
            >
              {value}
            </button>
          ))}
        </div>
      }
    >
      {subtitle && <p className="mb-3 text-xs text-secondary">{subtitle}</p>}
      {view === 'chart' ? chart : <DataTable table={table} />}
    </Card>
  )
}

function DataTable({ table }: { table: ChartTable }) {
  return (
    <div className="max-h-64 overflow-auto rounded-control border border-subtle">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-subtle text-left text-xs text-secondary">
          <tr>
            {table.head.map((label, index) => (
              <th key={label} scope="col" className={cx('px-3 py-1.5 font-medium', index > 0 && 'text-right')}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {table.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, index) => (
                <td key={index} className={cx('px-3 py-1.5', index > 0 ? 'text-right text-body tabular-nums' : 'text-primary')}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
