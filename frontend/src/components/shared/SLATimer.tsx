import { AlarmClock, CircleCheck } from 'lucide-react'
import { useDemoNow } from '@/hooks/useDemoNow'
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
  /** e.g. "Ack" or "Resolve". */
  label: string
  /** When the deadline was met (e.g. first acknowledgement); stops the countdown. */
  doneAt?: IsoTime | null
}

/** Live countdown against the demo clock; once done, shows whether the deadline was met. */
export function SLATimer({ start, due, label, doneAt }: SLATimerProps) {
  if (doneAt) {
    const late = mytToMs(doneAt) > mytToMs(due)
    return (
      <Badge tone={late ? 'error' : 'success'} icon={CircleCheck} title={`${label} done ${formatIsoTime(doneAt)}`}>
        {label} · {late ? 'met late' : 'met'}
      </Badge>
    )
  }
  return <Countdown start={start} due={due} label={label} />
}

function Countdown({ start, due, label }: Omit<SLATimerProps, 'doneAt'>) {
  const now = useDemoNow()
  const { state, remainingMs } = slaStatus(start, due, mytToMs(now))
  const time = formatDuration(remainingMs)
  return (
    <Badge tone={stateTone[state]} icon={AlarmClock} title={`${label} due ${formatIsoTime(due)}`}>
      {label} · {state === 'breached' ? `overdue ${time}` : `${time} left`}
    </Badge>
  )
}
