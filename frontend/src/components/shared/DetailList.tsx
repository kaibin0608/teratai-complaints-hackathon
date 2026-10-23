import type { ReactNode } from 'react'

export interface Detail {
  label: string
  value: ReactNode
}

/** Label → value rows. Rows with an empty value (null, undefined, '') are skipped. */
export function DetailList({ items }: { items: readonly Detail[] }) {
  const shown = items.filter(({ value }) => value !== null && value !== undefined && value !== '')
  return (
    <dl className="grid grid-cols-[minmax(7rem,auto)_1fr] gap-x-4 gap-y-1.5 text-sm">
      {shown.map(({ label, value }) => (
        <div key={label} className="contents">
          <dt className="text-secondary">{label}</dt>
          <dd className="min-w-0 text-primary">{value}</dd>
        </div>
      ))}
    </dl>
  )
}
