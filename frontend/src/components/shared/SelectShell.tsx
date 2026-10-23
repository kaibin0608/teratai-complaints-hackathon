import { ChevronDown } from 'lucide-react'
import type { ReactNode } from 'react'

/** Classes every select shares: the browser's own arrow is replaced by the chevron SelectShell draws. */
export const selectClass = 'appearance-none pr-9'

/** Wraps a select with one consistent chevron. The list itself stays the native, accessible one. */
export function SelectShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative">
      {children}
      <ChevronDown size={14} aria-hidden className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-secondary" />
    </div>
  )
}
