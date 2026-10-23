import type { ComplaintInput, IntakeAck } from '@/lib/types'
import { request } from './client'

export const intakeApi = {
  /**
   * The organisers' contract route (no login), the same one the judges' laptop posts to.
   * The same complaint ID posted again returns the existing case instead of creating a second one.
   */
  submit: (complaint: ComplaintInput) => request<IntakeAck>('/complaints', { method: 'POST', body: complaint }),
}
