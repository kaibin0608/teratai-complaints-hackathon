import { useId, type ComponentProps } from 'react'
import { cx } from '@/lib/cx'
import { controlClass, FieldShell } from './FieldShell'

interface TextFieldProps extends ComponentProps<'input'> {
  label: string
  hint?: string
}

export function TextField({ label, hint, id, required, className, ...props }: TextFieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  return (
    <FieldShell id={inputId} label={label} optional={required === false} hint={hint}>
      <input id={inputId} required={required} className={cx('h-9', controlClass, className)} {...props} />
    </FieldShell>
  )
}
