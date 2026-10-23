import type { ComponentProps } from 'react'
import { cx } from '@/lib/cx'
import { controlClass } from './FieldShell'
import { SelectShell, selectClass } from './SelectShell'

interface FilterSelectProps {
  label: string
  value: string | null
  onChange: (value: string | null) => void
  options: readonly (readonly [string, string])[]
  /** First entry, which clears the filter. Defaults to "<label>: any". */
  anyLabel?: string
  /** Extra classes for the select itself, e.g. `w-44` to cap a menu with long entries. */
  className?: string
}

/** A compact filter menu whose first entry ("Category: any") clears it; it turns pink once a value is chosen. */
export function FilterSelect({ label, value, onChange, options, anyLabel, className }: FilterSelectProps) {
  const props: ComponentProps<'select'> = {
    'aria-label': label,
    value: value ?? '',
    onChange: (event) => onChange(event.target.value || null),
  }
  return (
    <SelectShell>
      <select {...props} className={cx('h-9', selectClass, controlClass, value && 'border-brand-600 bg-brand-50 font-medium text-brand-800', className)}>
        <option value="">{anyLabel ?? `${label}: any`}</option>
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </SelectShell>
  )
}
