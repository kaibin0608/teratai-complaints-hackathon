import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type Notice, type Toast, type ToastInput } from './toast-context'

/** More than this and older toasts make way: a busy desk should never bury the screen. */
const MAX_VISIBLE = 3
/** The bell keeps this many; older ones drop off. */
const MAX_HISTORY = 30

/**
 * Holds the toasts and the recent-notifications history for the whole app. It sits above the router, so a toast
 * survives the move to the next case; the Toaster and the bell that draw them live inside the router (their links need it).
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [history, setHistory] = useState<Notice[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), [])

  const record = useCallback((input: ToastInput) => {
    const id = nextId.current++
    setHistory((current) => [{ ...input, id, at: Date.now(), read: false }, ...current].slice(0, MAX_HISTORY))
    return id
  }, [])

  const show = useCallback(
    (input: ToastInput) => {
      const id = record(input)
      setToasts((current) => {
        // The same message twice (a double click, a repeated export) shows once, as the newest.
        const others = current.filter((toast) => toast.title !== input.title || toast.description !== input.description)
        return [{ ...input, id }, ...others].slice(0, MAX_VISIBLE)
      })
    },
    [record],
  )

  const recordOnly = useCallback((input: ToastInput) => void record(input), [record])

  const markAllRead = useCallback(() => setHistory((current) => (current.some((n) => !n.read) ? current.map((n) => ({ ...n, read: true })) : current)), [])

  const clearHistory = useCallback(() => setHistory([]), [])

  const value = useMemo(
    () => ({ toasts, history, unread: history.filter((n) => !n.read).length, show, record: recordOnly, dismiss, markAllRead, clearHistory }),
    [toasts, history, show, recordOnly, dismiss, markAllRead, clearHistory],
  )
  return <ToastContext value={value}>{children}</ToastContext>
}
