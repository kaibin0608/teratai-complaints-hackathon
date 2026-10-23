/** The hue of a chart's marks. One hue per chart (the labels carry identity); literal classes so Tailwind generates them. */
export type ChartTone = 'teal' | 'blue' | 'purple' | 'amber' | 'grey'

export const BAR_FILL: Record<ChartTone, string> = {
  teal: 'bg-chart-2',
  blue: 'bg-chart-5',
  purple: 'bg-chart-3',
  amber: 'bg-chart-4',
  grey: 'bg-chart-6',
}

export const COLUMN_FILL: Record<ChartTone, string> = {
  teal: 'fill-chart-2',
  blue: 'fill-chart-5',
  purple: 'fill-chart-3',
  amber: 'fill-chart-4',
  grey: 'fill-chart-6',
}
