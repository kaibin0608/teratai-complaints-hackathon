import { createContext } from 'react'
import { makeNameOf, type NameOf } from '@/lib/people'

export const PeopleContext = createContext<NameOf>(makeNameOf([]))
