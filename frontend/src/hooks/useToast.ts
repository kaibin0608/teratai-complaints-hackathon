import { use } from 'react'
import { ToastContext, type ToastApi } from '@/context/toast-context'

/** `show()` a toast after something the user did; see lib/notifications.ts for the wording of each action. */
export function useToast(): ToastApi {
  const value = use(ToastContext)
  if (!value) throw new Error('useToast must be used inside <ToastProvider>')
  return value
}
