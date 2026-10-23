import { useId, type ComponentProps } from 'react'
import { cx } from '@/lib/cx'
import { controlClass, FieldShell } from './FieldShell'
import { SelectShell, selectClass } from './SelectShell'

interface SelectFieldProps extends ComponentProps<'select'> {
  label: string
  options: readonly { value: string; label: string }[]
  hint?: string
}

export function SelectField({ label, options, hint, id, required, className, ...props }: SelectFieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  return (
    <FieldShell id={inputId} label={label} optional={required === false} hint={hint}>
      <SelectShell>
        <select id={inputId} required={required} className={cx('h-9 w-full', selectClass, controlClass, className)} {...props}>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </SelectShell>
    </FieldShell>
  )
}
