import { AlarmClock, CircleCheck } from 'lucide-react'
import { useNow } from '@/hooks/useNow'
import { mytToMs } from '@/lib/clock'
import { formatDuration, formatIsoTime } from '@/lib/format'
import { slaStatus, type SlaState } from '@/lib/sla'
import type { IsoTime } from '@/lib/types'
import { Badge, type BadgeTone } from './Badge'

/** Colour System §5, SLA column: on track · at risk · breached. */
const stateTone: Record<SlaState, BadgeTone> = { on_track: 'success', at_risk: 'warning', breached: 'error' }

interface SLATimerProps {
  /** Start of the SLA window (the complaint's received_at). */
  start: IsoTime
  due: IsoTime
  /** e.g. "Ack" or "Resolve". Omit where the context names the deadline (a table column). */
  label?: string
  /** When the deadline was met (e.g. first acknowledgement); stops the countdown. */
  doneAt?: IsoTime | null
  /** Plain coloured text instead of a pill: for long lists where a column of red pills is too loud. */
  plain?: boolean
}

/** Live countdown against the current time; once done, shows whether the deadline was met. */
export function SLATimer({ start, due, label, doneAt, plain }: SLATimerProps) {
  if (doneAt) {
    const late = mytToMs(doneAt) > mytToMs(due)
    return (
      <Badge tone={late ? 'error' : 'success'} icon={CircleCheck} title={`${label ?? 'Deadline'} done ${formatIsoTime(doneAt)}`}>
        {withLabel(label, late ? 'met late' : 'met')}
      </Badge>
    )
  }
  return <Countdown start={start} due={due} label={label} plain={plain} />
}

const plainClass: Record<SlaState, string> = {
  on_track: 'text-success-700',
  at_risk: 'font-medium text-warning-800',
  breached: 'font-medium text-error-700',
}

function Countdown({ start, due, label, plain }: Omit<SLATimerProps, 'doneAt'>) {
  const now = useNow()
  const { state, remainingMs } = slaStatus(start, due, mytToMs(now))
  const time = formatDuration(remainingMs)
  if (plain) {
    return (
      <span title={`${label ?? 'Deadline'} due ${formatIsoTime(due)}`} className={`inline-flex items-center gap-1 text-xs tabular-nums ${plainClass[state]}`}>
        <AlarmClock size={12} aria-hidden />
        {withLabel(label, state === 'breached' ? `${time} overdue` : `${time} left`)}
      </span>
    )
  }
  return (
    <Badge tone={stateTone[state]} icon={AlarmClock} title={`${label ?? 'Deadline'} due ${formatIsoTime(due)}`}>
      {withLabel(label, state === 'breached' ? `overdue ${time}` : `${time} left`)}
    </Badge>
  )
}

const withLabel = (label: string | undefined, text: string) => (label ? `${label} · ${text}` : text)
