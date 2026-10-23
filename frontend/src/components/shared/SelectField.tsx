import { useId, type ComponentProps } from 'react'
import { cx } from '@/lib/cx'
import { controlClass, FieldShell } from './FieldShell'

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
      <select id={inputId} required={required} className={cx('h-9', controlClass, className)} {...props}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  )
}
