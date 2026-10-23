import { createContext } from 'react'
import type { User } from '@/lib/types'

export type AuthState =
  /** Restoring a saved session on page load. */
  | { status: 'loading'; user: null }
  | { status: 'signed_out'; user: null }
  | { status: 'signed_in'; user: User }

export type AuthContextValue = AuthState & {
  /** Throws ApiError on bad credentials or an unreachable server. */
  login: (username: string, password: string) => Promise<User>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
