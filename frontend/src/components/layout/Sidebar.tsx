import { LogOut } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router'
import logo from '@/assets/teratai-logo.png'
import { cx } from '@/lib/cx'
import type { User } from '@/lib/types'
import { DemoClock } from './DemoClock'
import { NAV_ITEMS } from './navigation'
import { UserCard } from './UserCard'

const itemClass = 'flex w-full items-center gap-2.5 rounded-control px-2.5 py-1.5 text-sm transition-colors'

interface SidebarProps {
  user: User
  onSignOut: () => void
}

/** Borderless navigation on the page background. */
export function Sidebar({ user, onSignOut }: SidebarProps) {
  const items = NAV_ITEMS.filter((item) => item.roles.includes(user.role))
  return (
    <aside className="flex w-sidebar shrink-0 flex-col">
      <div className="flex items-center gap-2.5 px-2 pt-1 pb-6">
        {/* multiply drops the logo's near-white background into the page colour */}
        <img src={logo} alt="" className="h-8 w-auto mix-blend-multiply" />
        <div className="leading-tight">
          <div className="font-display text-base font-semibold text-primary">Teratai Bank</div>
          <div className="text-xs text-secondary">Complaints Ops</div>
        </div>
      </div>

      <NavSection label="Main menu">
        {items.map(({ label, to, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cx(itemClass, isActive ? 'bg-neutral-100 font-medium text-primary' : 'text-body hover:bg-subtle hover:text-primary')
            }
          >
            {({ isActive }) => (
              <>
                <Icon size={16} aria-hidden className={isActive ? 'text-brand-600' : 'text-secondary'} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </NavSection>

      <NavSection label="Account">
        <button type="button" onClick={onSignOut} className={cx(itemClass, 'text-error-600 hover:bg-error-50')}>
          <LogOut size={16} aria-hidden />
          Sign out
        </button>
      </NavSection>

      <div className="mt-auto flex flex-col gap-3">
        <DemoClock />
        <UserCard user={user} />
      </div>
    </aside>
  )
}

function NavSection({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="mb-5">
      <h2 className="mb-1.5 flex items-center gap-2 px-2 font-sans text-[11px] font-medium uppercase tracking-wide text-secondary">
        {label}
        <span aria-hidden className="h-px flex-1 bg-neutral-200" />
      </h2>
      <div className="flex flex-col gap-0.5">{children}</div>
    </section>
  )
}
