import { ChevronLeft } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'

interface PageProps {
  title: ReactNode
  /** A link back to where the user came from (e.g. a case to its queue). */
  back?: { to: string; label: string }
  /** Badges or short facts shown next to the title. */
  meta?: ReactNode
  /** Right-aligned header actions; keep at most one primary button per view. */
  actions?: ReactNode
  /** A bar pinned below the scrolling content (e.g. a case's decision bar). */
  footer?: ReactNode
  children?: ReactNode
}

/** A screen inside the content panel: title bar with a hairline, scrolling content, optional pinned footer. */
export function Page({ title, back, meta, actions, footer, children }: PageProps) {
  return (
    <>
      <header className="flex min-h-header shrink-0 flex-wrap items-center justify-between gap-x-4 gap-y-1.5 border-b border-default px-card py-2">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
          {back && (
            <Link
              to={back.to}
              aria-label={back.label}
              title={back.label}
              className="-ml-1 rounded-control p-1 text-secondary hover:bg-subtle hover:text-primary"
            >
              <ChevronLeft size={18} aria-hidden />
            </Link>
          )}
          <h1 className="text-lg font-semibold whitespace-nowrap">{title}</h1>
          {meta && <div className="flex flex-wrap items-center gap-1.5">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-1.5">{actions}</div>}
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-card">{children}</div>
      {footer && <footer className="shrink-0 border-t border-default bg-card px-card py-3">{footer}</footer>}
    </>
  )
}
