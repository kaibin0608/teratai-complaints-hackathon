import type { ReactNode } from 'react'

interface TileProps {
  label: string
  /** The number: shown large in Geist. */
  value: ReactNode
  /** Supporting line under the number. */
  detail?: ReactNode
}

/** One KPI: label, large value, a supporting line. Borders, not shadows. */
export function Tile({ label, value, detail }: TileProps) {
  return (
    <div className="rounded-card border border-default bg-card p-card shadow-card">
      <p className="text-xs font-medium text-secondary">{label}</p>
      <p className="mt-1 font-display text-3xl font-semibold text-primary tabular-nums">{value}</p>
      {detail && <p className="mt-1 text-xs text-secondary">{detail}</p>}
    </div>
  )
}
