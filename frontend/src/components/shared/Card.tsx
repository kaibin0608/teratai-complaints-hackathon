import type { ReactNode } from 'react'
import { cx } from '@/lib/cx'

interface CardProps {
  title: ReactNode
  /** Right side of the card header: a badge, a count, a ghost button. */
  aside?: ReactNode
  className?: string
  children: ReactNode
}

/** Bordered section inside the content panel (borders, not shadows). */
export function Card({ title, aside, className, children }: CardProps) {
  return (
    <section className={cx('rounded-card border border-default bg-card shadow-card', className)}>
      <header className="flex items-center justify-between gap-3 border-b border-subtle px-card py-2.5">
        <h2 className="text-sm font-semibold">{title}</h2>
        {aside}
      </header>
      <div className="p-card">{children}</div>
    </section>
  )
}
