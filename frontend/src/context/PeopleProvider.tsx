import { useMemo, type ReactNode } from 'react'
import { usersApi } from '@/api/users'
import { useApi } from '@/hooks/useApi'
import { useAuth } from '@/hooks/useAuth'
import { makeNameOf } from '@/lib/people'
import type { User } from '@/lib/types'
import { PeopleContext } from './people-context'

/**
 * Names for every username on screen. Only the manager may list users (`GET /api/users`); everyone
 * else knows just their own name, so other people fall back to a readable form of their username.
 */
export function PeopleProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const manager = user?.role === 'manager'
  const listed = useApi<User[]>(`people:${manager ? 'all' : 'self'}`, (signal) => (manager ? usersApi.list(signal) : Promise.resolve([])))
  const nameOf = useMemo(() => {
    const people = listed.status === 'success' ? listed.data : []
    return makeNameOf(user ? [...people, user] : people)
  }, [listed, user])
  return <PeopleContext value={nameOf}>{children}</PeopleContext>
}
