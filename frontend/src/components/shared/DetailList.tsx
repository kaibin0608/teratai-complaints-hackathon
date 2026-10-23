import type { ReactNode } from 'react'

export interface Detail {
  label: string
  value: ReactNode
}

/** Label → value rows. Rows with nothing to show (null, undefined, false, '') are skipped, so `cond && <x />` works as a value. */
export function DetailList({ items }: { items: readonly Detail[] }) {
  const shown = items.filter(({ value }) => value !== null && value !== undefined && value !== false && value !== '')
  return (
    <dl className="grid grid-cols-[minmax(5.5rem,9rem)_1fr] gap-x-4 gap-y-1.5 text-sm">
      {shown.map(({ label, value }) => (
        <div key={label} className="contents">
          <dt className="text-secondary">{label}</dt>
          <dd className="min-w-0 text-primary [overflow-wrap:anywhere]">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
