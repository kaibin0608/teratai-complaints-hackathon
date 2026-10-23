import { FilePlus, Inbox, LayoutDashboard, ShieldAlert, type LucideIcon } from 'lucide-react'
import { paths } from '@/lib/paths'
import type { Role } from '@/lib/types'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  roles: readonly Role[]
}

/** Sidebar entries, in display order. Access rules must match routes.tsx. */
export const NAV_ITEMS: readonly NavItem[] = [
  { label: 'Console', to: paths.manager, icon: LayoutDashboard, roles: ['manager'] },
  { label: 'Resolution Desk', to: paths.officer, icon: Inbox, roles: ['officer', 'manager'] },
  { label: 'Investigation', to: paths.fraud, icon: ShieldAlert, roles: ['fraud', 'manager'] },
  { label: 'Intake', to: paths.intake, icon: FilePlus, roles: ['officer', 'fraud', 'manager'] },
]
