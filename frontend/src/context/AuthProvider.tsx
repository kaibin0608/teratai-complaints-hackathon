import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '@/api/auth'
import { setAuthToken, setUnauthorizedHandler } from '@/api/client'
import { AuthContext, type AuthContextValue, type AuthState } from './auth-context'
import { useToast } from '@/hooks/useToast'

/** Per tab, so officer / analyst / manager can be signed in side by side. */
const TOKEN_KEY = 'teratai.auth.token'

const tokenStore = {
  read(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  write(token: string | null): void {
    try {
      if (token) sessionStorage.setItem(TOKEN_KEY, token)
      else sessionStorage.removeItem(TOKEN_KEY)
    } catch {
      // Storage blocked: the session simply won't survive a refresh.
    }
  },
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() =>
    tokenStore.read() ? { status: 'loading', user: null } : { status: 'signed_out', user: null },
  )

  const logout = useCallback(() => {
    tokenStore.write(null)
    setAuthToken(null)
    setState({ status: 'signed_out', user: null })
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const { token, user } = await authApi.login({ username, password })
    tokenStore.write(token)
    setAuthToken(token)
    setState({ status: 'signed_in', user })
    return user
  }, [])

  // A 401 on a signed-in request ends the session, and says so on the login page.
  const { show, clearHistory } = useToast()
  useEffect(() => {
    setUnauthorizedHandler(() => {
      logout()
      clearHistory()
      show({ tone: 'warning', title: 'Your session has ended', description: 'Sign in again to carry on.' })
    })
    return () => setUnauthorizedHandler(null)
  }, [logout, show, clearHistory])

  // Restore a saved session once on load.
  useEffect(() => {
    const token = tokenStore.read()
    if (!token) return
    setAuthToken(token)
    const controller = new AbortController()
    authApi
      .me(controller.signal)
      .then((user) => setState({ status: 'signed_in', user }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        console.warn('Could not restore session', error)
        logout()
      })
    return () => controller.abort()
  }, [logout])

  const value = useMemo<AuthContextValue>(() => ({ ...state, login, logout }), [state, login, logout])

  return <AuthContext value={value}>{children}</AuthContext>
}
