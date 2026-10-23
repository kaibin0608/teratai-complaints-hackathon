import { useId, type ComponentProps } from 'react'
import { cx } from '@/lib/cx'
import { controlClass, FieldShell } from './FieldShell'

interface TextAreaProps extends ComponentProps<'textarea'> {
  label: string
  hint?: string
}

export function TextArea({ label, hint, id, required, className, ...props }: TextAreaProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  return (
    <FieldShell id={inputId} label={label} optional={required === false} hint={hint}>
      <textarea id={inputId} required={required} className={cx('py-2 leading-relaxed', controlClass, className)} {...props} />
    </FieldShell>
  )
}
