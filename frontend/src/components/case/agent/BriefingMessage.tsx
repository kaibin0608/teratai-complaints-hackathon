import { ChevronRight, CircleAlert, CircleCheck } from 'lucide-react'
import { useState } from 'react'
import { buildBriefing } from '@/lib/briefing'
import { cx } from '@/lib/cx'
import type { CaseDetail } from '@/lib/types'

/** The agent's opening message: what it did and recommends, with the steps behind it one click away. */
export function BriefingMessage({ detail }: { detail: CaseDetail }) {
  const { paragraphs, steps } = buildBriefing(detail)
  const [open, setOpen] = useState(false)
  return (
    <div className="flex flex-col gap-2">
      {paragraphs.map((text) => (
        <p key={text} className="text-sm leading-relaxed text-primary">
          {text}
        </p>
      ))}
      {steps.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            className="flex items-center gap-1 text-sm font-medium text-link hover:text-link-hover"
          >
            <ChevronRight size={14} aria-hidden className={cx('transition-transform', open && 'rotate-90')} />
            {open ? 'Hide how I got here' : 'Show how I got here'}
          </button>
          {open && (
            <ol className="mt-2 flex flex-col gap-2 border-l border-default pl-4">
              {steps.map((step) => {
                const Icon = step.state === 'done' ? CircleCheck : CircleAlert
                return (
                  <li key={step.label} className="relative text-sm">
                    <Icon size={14} aria-hidden className={cx('absolute top-0.5 -left-[1.4rem] bg-card', step.state === 'done' ? 'text-success-500' : 'text-warning-500')} />
                    <span className="font-medium text-primary">{step.label}</span>
                    <span className="block text-secondary">{step.detail}</span>
                  </li>
                )
              })}
            </ol>
          )}
        </div>
      )}
    </div>
  )
}
