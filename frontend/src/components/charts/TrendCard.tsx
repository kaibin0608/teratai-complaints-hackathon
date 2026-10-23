import { useState, type MouseEvent } from 'react'
import { categoryLabel } from '@/lib/labels'
import { CATEGORIES, type Metrics } from '@/lib/types'
import { ChartCard } from './ChartCard'

type Day = Metrics['trends']['received_by_day'][number]

const W = 720
const H = 190
const MARGIN = { top: 10, right: 8, bottom: 22, left: 34 }
const PLOT_W = W - MARGIN.left - MARGIN.right
const PLOT_H = H - MARGIN.top - MARGIN.bottom
const BAR_MAX = 24
const GAP = 2

/** 7 → 10, 43 → 50, 180 → 200: a clean top for the axis. */
function niceMax(value: number): number {
  const power = 10 ** Math.floor(Math.log10(Math.max(1, value)))
  const step = [1, 2, 5, 10].find((s) => s * power >= value) ?? 10
  return step * power
}

const shortDate = (date: string) => `${date.slice(8, 10)}-${date.slice(5, 7)}`

/** A column with a 4px rounded top and a square baseline. */
function columnPath(x: number, y: number, width: number, height: number): string {
  const r = Math.min(4, width / 2, height)
  return `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`
}

/** Complaints received per day (the day the complaint arrived, not when it was processed). One series, so one hue. */
export function TrendCard({ days }: { days: readonly Day[] }) {
  const [hover, setHover] = useState<number | null>(null)
  const max = niceMax(Math.max(1, ...days.map((d) => d.total)))
  const step = days.length > 0 ? PLOT_W / days.length : PLOT_W
  const barWidth = Math.max(2, Math.min(BAR_MAX, step - GAP))
  const y = (value: number) => MARGIN.top + PLOT_H - (value / max) * PLOT_H
  const ticks = [0, max / 2, max]
  const labelled = days.length > 2 ? [0, Math.floor((days.length - 1) / 2), days.length - 1] : days.map((_, i) => i)

  const onMove = (event: MouseEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    const x = ((event.clientX - box.left) / box.width) * W - MARGIN.left
    const index = Math.floor(x / step)
    setHover(index >= 0 && index < days.length ? index : null)
  }
  const active = hover !== null ? days[hover] : undefined

  return (
    <ChartCard
      title="Complaints received per day"
      subtitle={days.length > 0 ? `${days.length} days, ${shortDate(days[0]!.date)} to ${shortDate(days[days.length - 1]!.date)}` : undefined}
      table={{ head: ['Day', 'Complaints'], rows: days.map((d) => [d.date, d.total]) }}
      chart={
        days.length === 0 ? (
          <p className="py-6 text-center text-sm text-secondary">Nothing yet.</p>
        ) : (
          <div className="relative overflow-x-auto">
            <svg
              viewBox={`0 0 ${W} ${H}`}
              role="img"
              aria-label={`Complaints received per day: ${days.reduce((s, d) => s + d.total, 0)} in total`}
              className="min-w-[560px] w-full"
              onMouseMove={onMove}
              onMouseLeave={() => setHover(null)}
            >
              {ticks.map((tick) => (
                <g key={tick}>
                  <line x1={MARGIN.left} x2={W - MARGIN.right} y1={y(tick)} y2={y(tick)} className="stroke-neutral-100" strokeWidth={1} />
                  <text x={MARGIN.left - 6} y={y(tick) + 3} textAnchor="end" className="fill-neutral-500 text-[10px]">
                    {tick}
                  </text>
                </g>
              ))}
              {days.map((d, i) => {
                const x = MARGIN.left + i * step + (step - barWidth) / 2
                const height = (d.total / max) * PLOT_H
                return (
                  <g key={d.date}>
                    {hover === i && <rect x={MARGIN.left + i * step} y={MARGIN.top} width={step} height={PLOT_H} className="fill-neutral-50" />}
                    {d.total > 0 && <path d={columnPath(x, y(d.total), barWidth, height)} className="fill-chart-1" />}
                  </g>
                )
              })}
              {labelled.map((i) => (
                <text key={i} x={MARGIN.left + i * step + step / 2} y={H - 6} textAnchor={i === 0 ? 'start' : i === days.length - 1 ? 'end' : 'middle'} className="fill-neutral-500 text-[10px]">
                  {shortDate(days[i]!.date)}
                </text>
              ))}
            </svg>

            {active && hover !== null && (
              <div
                role="status"
                className="pointer-events-none absolute top-1 z-10 w-44 rounded-control bg-inverse px-2.5 py-2 text-xs text-inverse shadow-overlay"
                style={{ left: `${Math.min(Math.max(((MARGIN.left + hover * step) / W) * 100, 2), 70)}%` }}
              >
                <p className="font-medium">
                  {active.date}: {active.total} complaint{active.total === 1 ? '' : 's'}
                </p>
                {CATEGORIES.filter((c) => active.by_category[c] > 0).map((c) => (
                  <p key={c} className="flex justify-between gap-2 text-neutral-200">
                    <span>{categoryLabel[c]}</span>
                    <span className="tabular-nums">{active.by_category[c]}</span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )
      }
    />
  )
}
