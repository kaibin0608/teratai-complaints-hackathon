import { LogOut } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import logo from '@/assets/teratai-logo.png'
import { useWaitingCount } from '@/hooks/useWaitingCount'
import { cx } from '@/lib/cx'
import type { User } from '@/lib/types'
import { NAV_ITEMS } from './navigation'
import { NotificationBell } from './NotificationBell'
import { UserCard } from './UserCard'

const itemClass =
  'flex w-full items-center justify-center gap-2.5 rounded-control px-2.5 py-1.5 text-sm transition-colors xl:justify-start'

interface SidebarProps {
  user: User
  onSignOut: () => void
}

/** Borderless navigation on the page background. Below 1280 px it is an icon rail; labels move to tooltips. */
export function Sidebar({ user, onSignOut }: SidebarProps) {
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role))
  // Cases nobody has picked up yet, on the page where this person starts them.
  const waiting = useWaitingCount(user.role)
  return (
    <aside className="flex w-sidebar-rail shrink-0 flex-col xl:w-sidebar">
      <div className="flex items-center justify-center gap-2.5 px-2 pt-1 pb-6 xl:justify-start">
        {/* multiply drops the logo's near-white background into the page colour */}
        <img src={logo} alt="Teratai Bank" className="h-8 w-auto mix-blend-multiply" />
        <div className="hidden leading-tight xl:block">
          <div className="font-display text-base font-semibold text-primary">Teratai Bank</div>
          <div className="text-xs text-secondary">Complaints Ops</div>
        </div>
      </div>

      <NavSection label="Main menu">
        {items.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            aria-label={label}
            className={({ isActive }) =>
              cx(itemClass, isActive ? 'bg-neutral-100 font-medium text-primary' : 'text-body hover:bg-subtle hover:text-primary')
            }
          >
            {({ isActive }) => {
              const count = to === waiting.to ? waiting.count : null
              return (
                <>
                  <span className="relative shrink-0">
                    <Icon size={16} aria-hidden className={isActive ? 'text-brand-600' : 'text-secondary'} />
                    {/* In the icon rail the number has no room: a dot says "something is waiting". */}
                    {count ? <span aria-hidden className="absolute -top-1 -right-1 size-2 rounded-full bg-brand-600 xl:hidden" /> : null}
                  </span>
                  <span className="hidden xl:inline">{label}</span>
                  {count ? (
                    <span title={`${count} waiting`} className="ml-auto hidden rounded-badge bg-brand-600 px-1.5 text-[11px] font-medium text-inverse tabular-nums xl:inline">
                      {count}
                    </span>
                  ) : null}
                </>
              )
            }}
          </NavLink>
        ))}
      </NavSection>

      <NavSection label="Account">
        <NotificationBell itemClass={itemClass} />
        <button type="button" onClick={onSignOut} title="Sign out" aria-label="Sign out" className={cx(itemClass, 'text-error-600 hover:bg-error-50')}>
          <LogOut size={16} aria-hidden className="shrink-0" />
          <span className="hidden xl:inline">Sign out</span>
        </button>
      </NavSection>

      <div className="mt-auto flex flex-col gap-3">
        <UserCard user={user} />
      </div>
    </aside>
  )
}

function NavSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="mb-5">
      <h2 className="mb-1.5 hidden items-center gap-2 px-2 font-sans text-[11px] font-medium uppercase tracking-wide text-secondary xl:flex">
        {label}
        <span aria-hidden className="h-px flex-1 bg-neutral-200" />
      </h2>
      <div className="flex flex-col gap-0.5">{children}</div>
    </section>
  )
}
