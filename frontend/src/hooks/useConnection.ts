import { useSyncExternalStore } from 'react'
import { getConnection, subscribeConnection, type Connection } from '@/api/client'

/** Whether the backend is answering; updated by every request, so polling clears it on its own. */
export function useConnection(): Connection {
  return useSyncExternalStore(subscribeConnection, getConnection)
}
