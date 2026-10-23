import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type Toast, type ToastInput } from './toast-context'

/** More than this and older toasts make way: a busy desk should never bury the screen. */
const MAX_VISIBLE = 3

/**
 * Holds the toasts for the whole app. It sits above the router, so a toast survives the move to the next case;
 * the Toaster that draws them lives inside the router (its links need it).
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const dismiss = useCallback((id: number) => setToasts((current) => current.filter((toast) => toast.id !== id)), [])

  const show = useCallback((input: ToastInput) => {
    const id = nextId.current++
    setToasts((current) => {
      // The same message twice (a double click, a repeated export) shows once, as the newest.
      const others = current.filter((toast) => toast.title !== input.title || toast.description !== input.description)
      return [{ ...input, id }, ...others].slice(0, MAX_VISIBLE)
    })
  }, [])

  const value = useMemo(() => ({ toasts, show, dismiss }), [toasts, show, dismiss])
  return <ToastContext value={value}>{children}</ToastContext>
}
