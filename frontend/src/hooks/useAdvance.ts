import { useCallback } from 'react'
import { useNavigate } from 'react-router'
import { casesApi } from '@/api/cases'
import type { ActionKey } from '@/lib/actions'
import { doneMessage, homeAfter, nextCaseQuery, pickNext } from '@/lib/advance'
import { paths } from '@/lib/paths'
import { useAuth } from './useAuth'

/** What the page after an action shows, carried in the router state. */
export interface NoticeState {
  notice?: string
}

/** After an action that finishes the user's work on a case, open the next case that needs them (or their queue). */
export function useAdvance() {
  const navigate = useNavigate()
  const auth = useAuth()

  return useCallback(
    async (action: ActionKey, finishedId: string) => {
      if (auth.status !== 'signed_in') return
      const { user } = auth
      let nextId: string | undefined
      try {
        const list = await casesApi.list(nextCaseQuery(action, user))
        nextId = pickNext(list.items, finishedId, user)?.complaint_id
      } catch {
        // No lookup, no next case: fall back to the queue. The action itself already succeeded.
      }
      const tail = nextId ? 'Showing the next case that needs you.' : 'Nothing else is waiting for you.'
      navigate(nextId ? paths.case(nextId) : homeAfter(action, user), {
        state: { notice: `${doneMessage(action, finishedId)} ${tail}` } satisfies NoticeState,
      })
    },
    [auth, navigate],
  )
}
