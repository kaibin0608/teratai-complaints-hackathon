import { BAR_COLOURS } from '@/components/charts/chartTones'
import { categoryLabel } from '@/lib/labels'
import { CATEGORIES, type Category } from '@/lib/types'

/** A category as a coloured dot and its name, in the same colour the charts give it. For dense lists. */
export function CategoryTag({ category }: { category: Category }) {
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-body">
      <span aria-hidden className={`size-2 rounded-full ${BAR_COLOURS[CATEGORIES.indexOf(category)]}`} />
      {categoryLabel[category]}
    </span>
  )
}
