import { CircleCheck, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { useAuth } from '@/hooks/useAuth'
import { planActions, type ActionKey, type LimitInfo } from '@/lib/actions'
import { formatMoney } from '@/lib/format'
import type { CaseDetail } from '@/lib/types'
import { ActionDialog } from './ActionDialog'
import { ACTIONS } from './actionConfig'
import { useNameOf } from '@/hooks/useNameOf'

interface CaseActionsProps {
  detail: CaseDetail
  /** An action changed the case: re-fetch it. */
  onChanged: () => void
}

/**
 * The case's decision bar: the buttons this user may press, in a fixed order, with the approval
 * headroom beside them. Renders nothing when there is nothing to say or do.
 */
export function CaseActions({ detail, onChanged }: CaseActionsProps) {
  const auth = useAuth()
  const nameOf = useNameOf()
  const [open, setOpen] = useState<ActionKey | null>(null)
  if (auth.status !== 'signed_in') return null

  const { actions, notice, limit } = planActions(detail, auth.user, nameOf)
  if (actions.length === 0 && !notice) return null

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
        <div className="flex min-w-0 flex-col gap-0.5 text-sm">
          {limit && <Headroom info={limit} />}
          {notice && <p className="text-body">{notice}</p>}
        </div>
        <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
          {actions.map(({ key, emphasis, disabledReason }) => {
            const { label, icon: Icon } = ACTIONS[key]
            return (
              <span key={key} title={disabledReason}>
                <Button
                  variant={emphasis === 'danger' ? 'danger-outline' : emphasis}
                  disabled={Boolean(disabledReason)}
                  onClick={() => setOpen(key)}
                >
                  <Icon size={16} aria-hidden />
                  {label}
                </Button>
              </span>
            )
          })}
        </div>
      </div>
      <ActionDialog action={open} detail={detail} onClose={() => setOpen(null)} onChanged={onChanged} />
    </>
  )
}

/** "Your limit RM2,000.00 · this refund RM550.00 ✓" (UI_API.md: show the headroom before the click). */
function Headroom({ info }: { info: LimitInfo }) {
  const Icon = info.over ? TriangleAlert : CircleCheck
  return (
    <p className="flex flex-wrap items-center gap-1.5 text-secondary tabular-nums">
      Your limit {formatMoney(info.limit)} · {info.subject} {formatMoney(info.amount)}
      <Icon size={14} aria-hidden className={info.over ? 'text-warning-500' : 'text-success-500'} />
      <span className={info.over ? 'text-warning-800' : 'text-success-700'}>{info.over ? 'over your limit' : 'within your limit'}</span>
    </p>
  )
}
