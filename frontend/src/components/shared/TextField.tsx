import { useId, type ComponentProps } from 'react'
import { cx } from '@/lib/cx'

interface TextFieldProps extends ComponentProps<'input'> {
  label: string
}

/** Labelled text input (Colour System §4, input). */
export function TextField({ label, id, className, ...props }: TextFieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-primary">
        {label}
      </label>
      <input
        id={inputId}
        className={cx(
          'h-9 rounded-control border border-control bg-card px-3 text-sm text-primary placeholder:text-secondary',
          'hover:border-neutral-500 focus:border-focus disabled:border-default disabled:bg-subtle disabled:text-disabled',
          className,
        )}
        {...props}
      />
    </div>
  )
}
