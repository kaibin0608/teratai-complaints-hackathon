import type { Queue } from '@/lib/types'

/** Queue tabs per screen, in display order; the first is the default. The backend filters by role. */
export const OFFICER_TABS: readonly Queue[] = ['awaiting_approval', 'approved', 'rejected']
export const FRAUD_TABS: readonly Queue[] = ['with_fraud_team']
export const MANAGER_TABS: readonly Queue[] = [
  'awaiting_approval',
  'with_fraud_team',
  'auto_resolved',
  'approved',
  'rejected',
  'processing',
  'error',
]
