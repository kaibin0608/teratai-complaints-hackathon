import { formatMoney } from '@/lib/format'
import { roleLabel } from '@/lib/labels'
import type { User } from '@/lib/types'

/** Signed-in user, pinned to the bottom of the sidebar. In the icon rail only the initials show. */
export function UserCard({ user }: { user: User }) {
  const initials = user.full_name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
  const limit = user.approval_limit_myr === null ? 'No approval limit' : `Limit ${formatMoney(user.approval_limit_myr)}`

  return (
    <div
      title={`${user.full_name} · ${roleLabel[user.role]} · ${limit}`}
      className="flex items-center justify-center gap-2.5 rounded-card border border-default bg-card p-2 xl:justify-start"
    >
      <div
        aria-hidden
        className="grid size-9 shrink-0 place-items-center rounded-control bg-brand-50 text-sm font-semibold text-brand-700"
      >
        {initials}
      </div>
      <div className="hidden min-w-0 leading-tight xl:block">
        <div className="truncate text-sm font-medium text-primary">{user.full_name}</div>
        <div className="truncate text-[11px] font-medium uppercase tracking-wide text-secondary">{roleLabel[user.role]}</div>
        <div className="truncate text-xs tabular-nums text-secondary">{limit}</div>
      </div>
    </div>
  )
}
