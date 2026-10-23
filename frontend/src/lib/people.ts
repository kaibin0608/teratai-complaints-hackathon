/**
 * People are shown by name everywhere except the login form. The backend identifies them by username
 * (audit actors, assignments, escalations); this turns one into the name to display.
 */
import type { User } from './types'

export type NameOf = (username: string) => string

/** Used when a username has no known name: "officer2" → "Officer 2". */
function readable(username: string): string {
  const spaced = username.replace(/[._-]+/g, ' ').replace(/([a-z])(\d)/gi, '$1 $2').trim()
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

export function makeNameOf(people: readonly User[]): NameOf {
  const names = new Map(people.map((person) => [person.username, person.full_name]))
  return (username) => names.get(username) ?? readable(username)
}
