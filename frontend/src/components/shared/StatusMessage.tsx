import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface StatusMessageProps {
  icon: LucideIcon
  title: string
  children?: ReactNode
  /** e.g. a retry button or a link back. */
  action?: ReactNode
  /** Spin the icon (loading). */
  busy?: boolean
}

/** Centered message for loading, empty and error states. */
export function StatusMessage({ icon: Icon, title, children, action, busy = false }: StatusMessageProps) {
  return (
    <div role={busy ? 'status' : undefined} className="flex flex-col items-center py-16 text-center">
      <Icon size={24} aria-hidden className={busy ? 'animate-spin text-secondary' : 'text-secondary'} />
      <p className="mt-3 text-sm font-medium text-primary">{title}</p>
      {children && <p className="mt-1 max-w-sm text-sm text-secondary">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
