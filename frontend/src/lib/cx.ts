/** Join class names, skipping falsy values: cx('a', isActive && 'b'). */
export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}
