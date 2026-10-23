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

/** A past notification, kept for the bell's list. */
export interface Notice extends Toast {
  /** Epoch ms. */
  at: number
  read: boolean
}

export interface ToastApi {
  toasts: readonly Toast[]
  /** Newest first; only what this browser tab saw (the backend keeps no per-user notifications). */
  history: readonly Notice[]
  unread: number
  /** A toast now, and an entry in the history. */
  show: (toast: ToastInput) => void
  /** An entry in the history only: for background changes that should not interrupt (e.g. new cases arrived). */
  record: (notice: ToastInput) => void
  dismiss: (id: number) => void
  markAllRead: () => void
  /** On sign-out: the next person on this tab must not see the last one's notifications. */
  clearHistory: () => void
}

export const ToastContext = createContext<ToastApi | null>(null)
