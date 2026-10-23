import { useCallback, useEffect, useEffectEvent, useState } from 'react'

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: T }

interface UseApiOptions<T> {
  /** Refetch every `pollMs` (e.g. queues). Refreshes keep showing the current data. */
  pollMs?: number
  /** With `pollMs`: poll only while this is true for the loaded data (e.g. while the agent is working); never before data loads. */
  pollWhile?: (data: T) => boolean
}

/**
 * Load data from the API. `key` identifies the request (e.g. `case:CMP-00473`): a new key refetches,
 * cancels the stale request and shows "loading". `reload()` and polling refetch the same key while
 * keeping the current data on screen; a failed refresh keeps the last good data.
 */
export function useApi<T>(
  key: string,
  fetcher: (signal: AbortSignal) => Promise<T>,
  { pollMs, pollWhile }: UseApiOptions<T> = {},
): ApiState<T> & { reload: () => void } {
  const [version, setVersion] = useState(0)
  const [settled, setSettled] = useState<{ key: string; state: ApiState<T> } | null>(null)
  const load = useEffectEvent((signal: AbortSignal) => fetcher(signal))

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
      .then((data) => setSettled({ key, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const failed: ApiState<T> = { status: 'error', error: error instanceof Error ? error : new Error(String(error)) }
        setSettled((previous) =>
          previous?.key === key && previous.state.status === 'success' ? previous : { key, state: failed },
        )
      })
    return () => controller.abort()
  }, [key, version])

  const state: ApiState<T> = settled?.key === key ? settled.state : { status: 'loading' }
  const polling = pollMs !== undefined && (state.status === 'success' ? !pollWhile || pollWhile(state.data) : !pollWhile)

  useEffect(() => {
    if (!polling) return
    const timer = setInterval(() => setVersion((v) => v + 1), pollMs)
    return () => clearInterval(timer)
  }, [key, pollMs, polling])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  return { ...state, reload }
}
