/**
 * Marks are coloured by what they stand for, in this fixed order (never by rank, so sorting does not repaint them).
 * Every mark also has its label beside it or a legend, so colour is never the only way to tell them apart.
 * Literal class names so Tailwind generates them.
 */
export const BAR_COLOURS = ['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5', 'bg-chart-6', 'bg-chart-7'] as const
export const SEGMENT_FILLS = ['fill-chart-1', 'fill-chart-2', 'fill-chart-3', 'fill-chart-4', 'fill-chart-5', 'fill-chart-6', 'fill-chart-7'] as const
