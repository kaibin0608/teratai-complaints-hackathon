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
}

/** Live countdown against the current time; once done, shows whether the deadline was met. */
export function SLATimer({ start, due, label, doneAt }: SLATimerProps) {
  if (doneAt) {
    const late = mytToMs(doneAt) > mytToMs(due)
    return (
      <Badge tone={late ? 'error' : 'success'} icon={CircleCheck} title={`${label ?? 'Deadline'} done ${formatIsoTime(doneAt)}`}>
        {withLabel(label, late ? 'met late' : 'met')}
      </Badge>
    )
  }
  return <Countdown start={start} due={due} label={label} />
}

function Countdown({ start, due, label }: Omit<SLATimerProps, 'doneAt'>) {
  const now = useNow()
  const { state, remainingMs } = slaStatus(start, due, mytToMs(now))
  const time = formatDuration(remainingMs)
  return (
    <Badge tone={stateTone[state]} icon={AlarmClock} title={`${label ?? 'Deadline'} due ${formatIsoTime(due)}`}>
      {withLabel(label, state === 'breached' ? `overdue ${time}` : `${time} left`)}
    </Badge>
  )
}

const withLabel = (label: string | undefined, text: string) => (label ? `${label} · ${text}` : text)
