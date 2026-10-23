import { CircleAlert, CircleCheck, Info, TriangleAlert, X, type LucideIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import type { Toast, ToastTone } from '@/context/toast-context'
import { useToast } from '@/hooks/useToast'
import { cx } from '@/lib/cx'

/** Long enough to read two lines; errors stay longer. Hovering or focusing a toast pauses it. */
const DURATION_MS: Record<ToastTone, number> = { success: 5000, info: 5000, neutral: 5000, warning: 7000, error: 9000 }

const TONE: Record<ToastTone, { icon: LucideIcon; iconClass: string; bar: string }> = {
  success: { icon: CircleCheck, iconClass: 'text-success-500', bar: 'bg-success-500' },
  info: { icon: Info, iconClass: 'text-info-500', bar: 'bg-info-500' },
  neutral: { icon: CircleCheck, iconClass: 'text-neutral-500', bar: 'bg-neutral-400' },
  warning: { icon: TriangleAlert, iconClass: 'text-warning-500', bar: 'bg-warning-400' },
  error: { icon: CircleAlert, iconClass: 'text-error-500', bar: 'bg-error-500' },
}

/**
 * Bottom-right stack, newest on top, raised clear of the case page's action bar (its Approve button sits bottom-right). Successes are announced politely, errors at once; a toast never takes focus.
 * Rendered once, inside the router, by RootLayout.
 */
export function Toaster() {
  const { toasts, dismiss } = useToast()
  const polite = toasts.filter((toast) => toast.tone !== 'error')
  const urgent = toasts.filter((toast) => toast.tone === 'error')
  return (
    <div className="pointer-events-none fixed right-6 bottom-24 z-50 flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col gap-2">
      <ol aria-live="assertive" aria-label="Errors" className="flex flex-col gap-2">
        {urgent.map((toast) => (
          <ToastItem key={toast.id} toast={toast} dismiss={dismiss} />
        ))}
      </ol>
      <ol aria-live="polite" aria-label="Notifications" className="flex flex-col gap-2">
        {polite.map((toast) => (
          <ToastItem key={toast.id} toast={toast} dismiss={dismiss} />
        ))}
      </ol>
    </div>
  )
}

function ToastItem({ toast, dismiss }: { toast: Toast; dismiss: (id: number) => void }) {
  const [paused, setPaused] = useState(false)
  const onDismiss = () => dismiss(toast.id)
  const { icon: Icon, iconClass, bar } = TONE[toast.tone]

  useEffect(() => {
    if (paused) return
    // Keyed on the toast, not on the list: another toast arriving does not restart this one's countdown.
    const timer = setTimeout(() => dismiss(toast.id), DURATION_MS[toast.tone])
    return () => clearTimeout(timer)
  }, [paused, dismiss, toast.id, toast.tone])

  return (
    <li
      role={toast.tone === 'error' ? 'alert' : 'status'}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="pointer-events-auto relative flex animate-[toast-in_160ms_ease-out] gap-3 overflow-hidden rounded-card border border-default bg-card py-3 pr-9 pl-4 shadow-overlay"
    >
      <span aria-hidden className={cx('absolute inset-y-0 left-0 w-1', bar)} />
      <Icon size={18} aria-hidden className={cx('mt-0.5 shrink-0', iconClass)} />
      <div className="min-w-0">
        <p className="text-sm font-medium text-primary">{toast.title}</p>
        {toast.description && <p className="mt-0.5 text-sm text-secondary">{toast.description}</p>}
        {toast.link && (
          <Link to={toast.link.to} onClick={onDismiss} className="mt-1 inline-block text-sm font-medium text-link hover:text-link-hover">
            {toast.link.label}
          </Link>
        )}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="absolute top-2 right-2 grid size-6 place-items-center rounded-control text-secondary hover:bg-neutral-100 hover:text-primary"
      >
        <X size={14} aria-hidden />
      </button>
    </li>
  )
}
