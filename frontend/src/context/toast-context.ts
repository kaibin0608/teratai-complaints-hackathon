import { createContext } from 'react'

/** success: something you did worked · info: it moved somewhere · warning: it needs more care now · error: it failed · neutral: done, nothing sent. */
export type ToastTone = 'success' | 'info' | 'warning' | 'error' | 'neutral'

export interface ToastInput {
  tone: ToastTone
  /** One line: past-tense verb, the case, the result. "Approved CMP-00244". */
  title: string
  /** The consequence, when it is not obvious. "RM550.00 refund and reply sent (simulated)." */
  description?: string
  /** A way back to what the toast is about, e.g. the case you just left. */
  link?: { label: string; to: string }
}

export interface Toast extends ToastInput {
  id: number
}

export interface ToastApi {
  toasts: readonly Toast[]
  show: (toast: ToastInput) => void
  dismiss: (id: number) => void
}

export const ToastContext = createContext<ToastApi | null>(null)
