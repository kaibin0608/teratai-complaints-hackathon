import { useCallback, useEffect, useEffectEvent, useState } from 'react'

export type ApiState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: T }

/**
 * Load data from the API. `key` identifies the request (e.g. `case:CMP-00473`): a new key refetches
 * and cancels the stale request. `reload()` refetches the same key, e.g. after an action.
 * State is derived per key, so switching keys shows "loading" without an extra render.
 */
export function useApi<T>(key: string, fetcher: (signal: AbortSignal) => Promise<T>): ApiState<T> & { reload: () => void } {
  const [version, setVersion] = useState(0)
  const requestKey = `${key}#${version}`
  const [settled, setSettled] = useState<{ key: string; state: ApiState<T> } | null>(null)
  const load = useEffectEvent((signal: AbortSignal) => fetcher(signal))

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
      .then((data) => setSettled({ key: requestKey, state: { status: 'success', data } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        const state: ApiState<T> = { status: 'error', error: error instanceof Error ? error : new Error(String(error)) }
        setSettled({ key: requestKey, state })
      })
    return () => controller.abort()
  }, [requestKey])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const state: ApiState<T> = settled?.key === requestKey ? settled.state : { status: 'loading' }
  return { ...state, reload }
}
