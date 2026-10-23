import { Outlet } from 'react-router'
import { useAuth } from '@/hooks/useAuth'
import { Sidebar } from './Sidebar'

/**
 * Frame for every signed-in screen: a borderless sidebar on the page background,
 * and one bordered content panel. Pages render inside the panel via <Page>.
 */
export function AppLayout() {
  const auth = useAuth()
  if (auth.status !== 'signed_in') return null
  return (
    <div className="flex h-dvh gap-frame p-frame">
      <Sidebar user={auth.user} onSignOut={auth.logout} />
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-card border border-default bg-card shadow-card">
        <Outlet />
      </main>
    </div>
  )
}
