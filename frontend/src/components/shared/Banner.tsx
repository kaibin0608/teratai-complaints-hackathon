import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cx } from '@/lib/cx'

type BannerTone = 'info' | 'warning' | 'error' | 'aubergine'

/** Colour System §5: banner = status 50 bg, 200 border, 800 text, 500 icon. */
const toneClass: Record<BannerTone, { box: string; icon: string }> = {
  info: { box: 'border-info-200 bg-info-50 text-info-800', icon: 'text-info-500' },
  warning: { box: 'border-warning-200 bg-warning-50 text-warning-800', icon: 'text-warning-500' },
  error: { box: 'border-error-200 bg-error-50 text-error-800', icon: 'text-error-500' },
  aubergine: { box: 'border-aubergine-200 bg-aubergine-50 text-aubergine-800', icon: 'text-aubergine-500' },
}

interface BannerProps {
  tone: BannerTone
  icon: LucideIcon
  title: ReactNode
  children?: ReactNode
}

export function Banner({ tone, icon: Icon, title, children }: BannerProps) {
  const style = toneClass[tone]
  return (
    <div role="status" className={cx('flex items-start gap-2.5 rounded-control border px-3 py-2.5 text-sm', style.box)}>
      <Icon size={16} aria-hidden className={cx('mt-0.5 shrink-0', style.icon)} />
      <div>
        <div className="font-medium">{title}</div>
        {children && <div className="mt-0.5">{children}</div>}
      </div>
    </div>
  )
}
