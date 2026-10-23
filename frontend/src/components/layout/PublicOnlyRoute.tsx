import { Navigate, Outlet, useLocation, type Location } from 'react-router'
import { useAuth } from '@/hooks/useAuth'
import { homeFor } from '@/lib/paths'

/**
 * Pages for signed-out users only (login). Once signed in, go back to the page that sent the
 * user to login (ProtectedRoute's `from`), otherwise to their home screen.
 */
export function PublicOnlyRoute() {
  const auth = useAuth()
  const location = useLocation()
  if (auth.status === 'loading') return null
  if (auth.status === 'signed_in') {
    const from = (location.state as { from?: Location } | null)?.from
    return <Navigate to={from ?? homeFor[auth.user.role]} replace />
  }
  return <Outlet />
}
