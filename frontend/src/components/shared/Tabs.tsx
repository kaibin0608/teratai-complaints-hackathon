import { cx } from '@/lib/cx'

export interface TabItem<T extends string> {
  value: T
  label: string
  count?: number
}

interface TabsProps<T extends string> {
  label: string
  items: readonly TabItem<T>[]
  value: T
  onChange: (value: T) => void
}

/** Colour System §4 tab: neutral.500 text, neutral.900 on hover / active, 2px brand.600 underline when active. */
export function Tabs<T extends string>({ label, items, value, onChange }: TabsProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="flex gap-5 border-b border-default">
      {items.map((item) => {
        const active = item.value === value
        return (
          <button
            key={item.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cx(
              '-mb-px flex items-center gap-1.5 border-b-2 pb-2 text-sm whitespace-nowrap transition-colors',
              active ? 'border-brand-600 font-medium text-primary' : 'border-transparent text-secondary hover:text-primary',
            )}
          >
            {item.label}
            {item.count !== undefined && (
              <span
                className={cx(
                  'rounded-badge px-1.5 text-xs tabular-nums',
                  active ? 'bg-brand-50 text-brand-800' : 'bg-neutral-100 text-neutral-600',
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
