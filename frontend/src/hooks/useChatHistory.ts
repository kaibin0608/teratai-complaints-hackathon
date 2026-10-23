import { useCallback, useState } from 'react'
import type { ChatTurn } from '@/api/chat'

const key = (owner: string, complaintId: string) => `chat:${owner}:${complaintId}`

function read(storageKey: string): ChatTurn[] {
  try {
    const parsed: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? '[]')
    return Array.isArray(parsed) ? (parsed as ChatTurn[]) : []
  } catch {
    return []
  }
}

/**
 * A case's conversation, kept for this tab so moving to the next case and back does not lose it. It is per person
 * (a second person signing in on the same tab starts clean) and per case. Storage can be blocked: it then just resets.
 */
export function useChatHistory(owner: string, complaintId: string) {
  const storageKey = key(owner, complaintId)
  const [turns, setTurnsState] = useState<ChatTurn[]>(() => read(storageKey))

  const setTurns = useCallback(
    (next: ChatTurn[]) => {
      setTurnsState(next)
      try {
        sessionStorage.setItem(storageKey, JSON.stringify(next))
      } catch {
        // Storage full or blocked: the conversation still works, it just won't survive leaving the page.
      }
    },
    [storageKey],
  )

  return [turns, setTurns] as const
}
