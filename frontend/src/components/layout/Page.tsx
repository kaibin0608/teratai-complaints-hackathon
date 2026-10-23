import type { ReactNode } from 'react'

interface PageProps {
  title: ReactNode
  /** Badges or short facts shown next to the title. */
  meta?: ReactNode
  /** Right-aligned header actions; keep at most one primary button per view. */
  actions?: ReactNode
  children?: ReactNode
}

/** A screen inside the content panel: title bar with a hairline, then scrolling content. */
export function Page({ title, meta, actions, children }: PageProps) {
  return (
    <>
      <header className="flex h-header shrink-0 items-center justify-between gap-4 border-b border-default px-card">
        <div className="flex min-w-0 items-center gap-3">
          <h1 className="truncate text-lg font-semibold">{title}</h1>
          {meta && <div className="flex shrink-0 items-center gap-1.5">{meta}</div>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-card">{children}</div>
    </>
  )
}
