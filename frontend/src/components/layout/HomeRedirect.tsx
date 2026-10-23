import { Navigate } from 'react-router'
import { useAuth } from '@/hooks/useAuth'
import { homeFor, paths } from '@/lib/paths'

/** "/" and unknown URLs: the signed-in user's home screen, otherwise login. */
export function HomeRedirect() {
  const auth = useAuth()
  if (auth.status === 'loading') return null
  return <Navigate to={auth.status === 'signed_in' ? homeFor[auth.user.role] : paths.login} replace />
}
