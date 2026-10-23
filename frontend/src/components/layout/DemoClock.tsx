import { Clock } from 'lucide-react'
import { useDemoNow } from '@/hooks/useDemoNow'
import { formatIsoTime } from '@/lib/format'

/** The labelled demo clock that SLA timers are measured against. */
export function DemoClock() {
  const now = useDemoNow()
  return (
    <div className="flex items-center gap-2 px-2 text-xs whitespace-nowrap text-secondary">
      <Clock size={14} aria-hidden className="shrink-0" />
      <span>Demo clock</span>
      <time dateTime={now} className="ml-auto tabular-nums text-body">
        {formatIsoTime(now, { seconds: true })}
      </time>
    </div>
  )
}
