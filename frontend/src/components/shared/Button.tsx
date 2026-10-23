import type { ComponentProps } from 'react'
import { cx } from '@/lib/cx'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'

/** Colour System §4. Use one primary per view; everything else secondary or ghost. */
const variantClass: Record<Variant, string> = {
  primary:
    'bg-brand-600 text-inverse hover:bg-brand-700 active:bg-brand-800 disabled:bg-neutral-100 disabled:text-disabled',
  secondary:
    'border border-default bg-card text-body hover:bg-subtle active:bg-neutral-100 disabled:bg-card disabled:text-disabled',
  ghost: 'text-link hover:bg-brand-50 active:bg-brand-100 disabled:bg-transparent disabled:text-disabled',
  danger:
    'bg-error-600 text-inverse hover:bg-error-700 active:bg-error-800 disabled:bg-neutral-100 disabled:text-disabled',
}

interface ButtonProps extends ComponentProps<'button'> {
  variant?: Variant
}

export function Button({ variant = 'secondary', type = 'button', className, ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(
        'inline-flex h-9 items-center justify-center gap-2 rounded-control px-3 text-sm font-medium transition-colors disabled:cursor-not-allowed',
        variantClass[variant],
        className,
      )}
      {...props}
    />
  )
}
