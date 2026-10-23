import { FilePlus, Inbox, LayoutDashboard, Layers, Scale, ScrollText, ShieldAlert, type LucideIcon } from 'lucide-react'
import { paths } from '@/lib/paths'
import type { Role } from '@/lib/types'

export interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  roles: readonly Role[]
}

/** Sidebar entries, in display order. Each must be reachable for its roles in routes.tsx. */
export const NAV_ITEMS: readonly NavItem[] = [
  { label: 'Console', to: paths.manager, icon: LayoutDashboard, roles: ['manager'] },
  { label: 'Cases', to: paths.cases, icon: Layers, roles: ['manager'] },
  { label: 'Audit log', to: paths.audit, icon: ScrollText, roles: ['manager'] },
  { label: 'Resolution Desk', to: paths.officer, icon: Inbox, roles: ['officer'] },
  { label: 'Investigation', to: paths.fraud, icon: ShieldAlert, roles: ['fraud'] },
  { label: 'Intake', to: paths.intake, icon: FilePlus, roles: ['officer', 'fraud', 'manager'] },
  { label: 'Policy', to: paths.policy, icon: Scale, roles: ['manager'] },
]
