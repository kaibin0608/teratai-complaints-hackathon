import type { User } from '@/lib/types'
import { request } from './client'

export const usersApi = {
  /** Manager only: for the reassign menu. */
  list: (signal?: AbortSignal) => request<User[]>('/api/users', { signal }),
}
