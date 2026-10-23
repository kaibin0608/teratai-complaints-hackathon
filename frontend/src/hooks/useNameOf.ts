import { use } from 'react'
import { PeopleContext } from '@/context/people-context'

/** Turns a username into the person's name for display. */
export function useNameOf() {
  return use(PeopleContext)
}
