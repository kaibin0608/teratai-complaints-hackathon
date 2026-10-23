import { categoryLabel } from '@/lib/labels'
import { CATEGORIES, type Category } from '@/lib/types'

/** One colour per category, in the order of CATEGORIES. Literal class names so Tailwind generates them. */
const DOT = ['bg-chart-1', 'bg-chart-2', 'bg-chart-3', 'bg-chart-4', 'bg-chart-5', 'bg-chart-6', 'bg-chart-7'] as const

/** A category as a coloured dot and its name, for dense lists. */
export function CategoryTag({ category }: { category: Category }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-body">
      <span aria-hidden className={`size-2 rounded-full ${DOT[CATEGORIES.indexOf(category)]}`} />
      {categoryLabel[category]}
    </span>
  )
}
