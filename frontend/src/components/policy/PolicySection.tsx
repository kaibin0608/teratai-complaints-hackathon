import type { ReactNode } from 'react'

interface PolicySectionProps {
  id: string
  title: string
  /** One line on what the section is and where it comes from. */
  description: string
  children: ReactNode
}

/** A titled block of the Policy page; `id` is the anchor the page's contents list links to. */
export function PolicySection({ id, title, description, children }: PolicySectionProps) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="flex scroll-mt-4 flex-col gap-3">
      <div>
        <h2 id={`${id}-title`} className="text-base font-semibold">
          {title}
        </h2>
        <p className="mt-0.5 text-sm text-secondary">{description}</p>
      </div>
      {children}
    </section>
  )
}
