/**
 * Marks are coloured by what they stand for, in this fixed order (never by rank, so sorting does not repaint them).
 * Every bar also has its label beside it, so colour is never the only way to tell them apart.
 * Literal class names so Tailwind generates them.
 */
export const BAR_COLOURS = ['bg-chart-2', 'bg-chart-5', 'bg-chart-3', 'bg-chart-4', 'bg-chart-1', 'bg-chart-7', 'bg-chart-6'] as const

/** Trend columns are one series, so one hue. */
export const COLUMN_FILL = 'fill-chart-2'
