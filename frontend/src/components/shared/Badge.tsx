import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cx } from '@/lib/cx'

export type BadgeTone = 'success' | 'warning' | 'error' | 'info' | 'neutral' | 'tag' | 'brand' | 'aubergine'

/**
 * Colour System §5–6: subtle badge = 50 bg + 700 text + 500 icon, no border, 20px tall.
 * Warning text uses 800. `tag` is the default neutral tag (product, channel, category).
 */
const toneClass: Record<BadgeTone, { box: string; icon: string }> = {
  success: { box: 'bg-success-50 text-success-700', icon: 'text-success-500' },
  warning: { box: 'bg-warning-50 text-warning-800', icon: 'text-warning-500' },
  error: { box: 'bg-error-50 text-error-700', icon: 'text-error-500' },
  info: { box: 'bg-info-50 text-info-700', icon: 'text-info-500' },
  neutral: { box: 'bg-neutral-100 text-neutral-600', icon: 'text-neutral-500' },
  tag: { box: 'bg-neutral-100 text-neutral-700', icon: 'text-neutral-500' },
  brand: { box: 'bg-brand-50 text-brand-800', icon: 'text-brand-600' },
  aubergine: { box: 'bg-aubergine-50 text-aubergine-700', icon: 'text-aubergine-500' },
}

interface BadgeProps {
  tone: BadgeTone
  /** Solid fill. Reserved for P1 (and destructive states): solid error.600, white text. */
  solid?: boolean
  /** Status is colour + icon + label; pass an icon for every status badge. */
  icon?: LucideIcon
  title?: string
  children: ReactNode
}

export function Badge({ tone, solid = false, icon: Icon, title, children }: BadgeProps) {
  const style = toneClass[tone]
  return (
    <span
      title={title}
      className={cx(
        'inline-flex h-5 items-center gap-1 rounded-badge px-1.5 text-xs font-medium whitespace-nowrap',
        solid ? 'bg-error-600 text-inverse' : style.box,
      )}
    >
      {Icon && <Icon size={12} strokeWidth={2.25} aria-hidden className={solid ? undefined : style.icon} />}
      {children}
    </span>
  )
}
