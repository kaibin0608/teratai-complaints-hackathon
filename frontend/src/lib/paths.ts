import type { Role } from './types'

/** Every URL in the app. Build links from here, never from string literals. */
export const paths = {
  root: '/',
  login: '/login',
  intake: '/intake',
  officer: '/officer',
  fraud: '/fraud',
  manager: '/manager',
  /** Every queue (manager). */
  cases: '/cases',
  audit: '/audit',
  /** The bank's fixed policy, read-only (manager). */
  policy: '/policy',
  case: (complaintId: string) => `/cases/${encodeURIComponent(complaintId)}`,
  /** Development only. */
} as const

/** Where each role lands after sign-in (PLAN.md §3.2). */
export const homeFor: Record<Role, string> = {
  officer: paths.officer,
  fraud: paths.fraud,
  manager: paths.manager,
}
