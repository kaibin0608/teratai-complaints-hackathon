import { Outlet } from 'react-router'
import { useAuth } from '@/hooks/useAuth'
import { useToast } from '@/hooks/useToast'
import { ConnectionBanner } from './ConnectionBanner'
import { Sidebar } from './Sidebar'
import { PeopleProvider } from '@/context/PeopleProvider'

/**
 * Frame for every signed-in screen: a borderless sidebar on the page background,
 * and one bordered content panel. Pages render inside the panel via <Page>.
 */
export function AppLayout() {
  const auth = useAuth()
  const toast = useToast()
  if (auth.status !== 'signed_in') return null
  return (
    <PeopleProvider>
      <div className="flex h-dvh gap-frame p-frame">
        <Sidebar user={auth.user} onSignOut={() => {
            auth.logout()
            toast.clearHistory()
            toast.show({ tone: 'neutral', title: 'You have signed out' })
          }} />
        <main className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-card border border-default bg-card shadow-card">
          <ConnectionBanner />
        <Outlet />
        </main>
      </div>
    </PeopleProvider>
  )
}
