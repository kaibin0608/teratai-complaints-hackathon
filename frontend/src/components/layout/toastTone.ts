import { CircleAlert, CircleCheck, Info, TriangleAlert, type LucideIcon } from 'lucide-react'
import type { ToastTone } from '@/context/toast-context'

/** Icon and colour per tone, shared by the toasts and the notifications list. Literal classes so Tailwind generates them. */
export const TONE: Record<ToastTone, { icon: LucideIcon; iconClass: string; bar: string }> = {
  success: { icon: CircleCheck, iconClass: 'text-success-500', bar: 'bg-success-500' },
  info: { icon: Info, iconClass: 'text-info-500', bar: 'bg-info-500' },
  neutral: { icon: CircleCheck, iconClass: 'text-neutral-500', bar: 'bg-neutral-400' },
  warning: { icon: TriangleAlert, iconClass: 'text-warning-500', bar: 'bg-warning-400' },
  error: { icon: CircleAlert, iconClass: 'text-error-500', bar: 'bg-error-500' },
}
