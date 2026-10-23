import { useCallback } from 'react'
import { useNavigate } from 'react-router'
import { casesApi } from '@/api/cases'
import type { ActionKey } from '@/lib/actions'
import { homeAfter, nextCaseQuery, pickNext } from '@/lib/advance'
import type { Advanced } from '@/lib/notifications'
import { paths } from '@/lib/paths'
import { useAuth } from './useAuth'

/** After an action that finishes the user's work on a case, open the next case that needs them (or their queue). */
export function useAdvance() {
  const navigate = useNavigate()
  const auth = useAuth()

  return useCallback(
    async (action: ActionKey, finishedId: string): Promise<Advanced> => {
      if (auth.status !== 'signed_in') return 'queue'
      const { user } = auth
      let nextId: string | undefined
      try {
        const list = await casesApi.list(nextCaseQuery(action, user))
        nextId = pickNext(list.items, finishedId, user)?.complaint_id
      } catch {
        // No lookup, no next case: fall back to the queue. The action itself already succeeded.
      }
      navigate(nextId ? paths.case(nextId) : homeAfter(action, user))
      return nextId ? 'next-case' : 'queue'
    },
    [auth, navigate],
  )
}
