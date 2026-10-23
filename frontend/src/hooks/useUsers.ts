import { usersApi } from '@/api/users'
import type { User } from '@/lib/types'
import { useApi } from './useApi'

export function useUsers() {
  return useApi<User[]>('users', (signal) => usersApi.list(signal))
}
