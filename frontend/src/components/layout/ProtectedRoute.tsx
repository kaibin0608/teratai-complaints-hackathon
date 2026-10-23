import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '@/hooks/useAuth'
import { homeFor, paths } from '@/lib/paths'
import type { Role } from '@/lib/types'

interface ProtectedRouteProps {
  /** Roles allowed through; omit to allow any signed-in user. */
  roles?: readonly Role[]
}

/**
 * Route guard. Signed-out users go to login (and come back afterwards); a role outside
 * `roles` goes to its own home screen. The backend enforces roles too; this only hides.
 */
export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const auth = useAuth()
  const location = useLocation()

  if (auth.status === 'loading') return null
  if (auth.status === 'signed_out') return <Navigate to={paths.login} replace state={{ from: location }} />
  if (roles && !roles.includes(auth.user.role)) return <Navigate to={homeFor[auth.user.role]} replace />
  return <Outlet />
}
