import type { ReactNode } from 'react'

interface FieldShellProps {
  id: string
  label: string
  /** Shown beside the label for fields that are not required. */
  optional?: boolean
  hint?: string
  children: ReactNode
}

/** Label, optional marker and hint around any form control, so every field looks the same. */
export function FieldShell({ id, label, optional, hint, children }: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-primary">
        {label}
        {optional && <span className="ml-1 font-normal text-secondary">(optional)</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-secondary">{hint}</p>}
    </div>
  )
}

/** Shared control styling (Colour System §4, input). */
export const controlClass =
  'rounded-control border border-control bg-card px-3 text-sm text-primary placeholder:text-secondary hover:border-neutral-500 focus:border-focus disabled:border-default disabled:bg-subtle disabled:text-disabled'
