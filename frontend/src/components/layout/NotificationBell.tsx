import { Bell } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useToast } from '@/hooks/useToast'
import { msToMyt } from '@/lib/clock'
import { cx } from '@/lib/cx'
import { TONE } from './toastTone'

/**
 * Recent notifications: the toasts you have seen, plus quiet entries such as new cases arriving.
 * Only what this browser tab saw; the backend keeps no per-user notifications.
 */
export function NotificationBell({ itemClass }: { itemClass: string }) {
  const { history, unread, markAllRead } = useToast()
  const [open, setOpen] = useState(false)
  // The entries that were new when the panel opened stay highlighted while it is open.
  const [fresh, setFresh] = useState<ReadonlySet<number>>(new Set())
  const box = useRef<HTMLDivElement>(null)

  function toggle() {
    if (!open) {
      setFresh(new Set(history.filter((n) => !n.read).map((n) => n.id)))
      markAllRead()
    }
    setOpen(!open)
  }

  useEffect(() => {
    if (!open) return
    const onPointer = (event: PointerEvent) => {
      if (!box.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={box} className="relative">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-haspopup="dialog"
        title="Notifications"
        aria-label={unread > 0 ? `Notifications, ${unread} new` : 'Notifications'}
        className={cx(itemClass, open ? 'bg-neutral-100 text-primary' : 'text-body hover:bg-subtle hover:text-primary')}
      >
        <span className="relative shrink-0">
          <Bell size={16} aria-hidden className="text-secondary" />
          {unread > 0 && <span aria-hidden className="absolute -top-1 -right-1 size-2 rounded-full bg-brand-600 ring-2 ring-[var(--background-color-page)]" />}
        </span>
        <span className="hidden xl:inline">Notifications</span>
        {unread > 0 && <span className="ml-auto hidden rounded-badge bg-brand-600 px-1.5 text-[11px] font-medium text-inverse tabular-nums xl:inline">{unread}</span>}
      </button>

      {open && (
        <div role="dialog" aria-label="Recent notifications" className="absolute top-0 left-full z-50 ml-3 w-96 rounded-card border border-default bg-card shadow-overlay">
          <header className="border-b border-subtle px-card py-2.5">
            <h2 className="text-sm font-semibold">Notifications</h2>
            <p className="text-xs text-secondary">What happened in this tab, newest first.</p>
          </header>
          {history.length === 0 ? (
            <p className="px-card py-6 text-center text-sm text-secondary">Nothing yet. Actions you take and new cases in your queue show up here.</p>
          ) : (
            <ol className="max-h-[28rem] divide-y divide-neutral-100 overflow-y-auto">
              {history.map((notice) => {
                const { icon: Icon, iconClass } = TONE[notice.tone]
                return (
                  <li key={notice.id} className={cx('flex gap-3 px-card py-2.5', fresh.has(notice.id) && 'bg-brand-50/60')}>
                    <Icon size={16} aria-hidden className={cx('mt-0.5 shrink-0', iconClass)} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-primary">{notice.title}</p>
                      {notice.description && <p className="mt-0.5 text-xs text-secondary">{notice.description}</p>}
                      {notice.link && (
                        <Link to={notice.link.to} onClick={() => setOpen(false)} className="mt-0.5 inline-block text-xs font-medium text-link hover:text-link-hover">
                          {notice.link.label}
                        </Link>
                      )}
                    </div>
                    <time className="shrink-0 text-xs text-secondary tabular-nums">{msToMyt(notice.at).slice(11, 16)}</time>
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
