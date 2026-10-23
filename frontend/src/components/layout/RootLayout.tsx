import { Outlet } from 'react-router'
import { Toaster } from './Toaster'

/** Wraps every route, signed in or not, so toasts show on any page (including after signing out). */
export function RootLayout() {
  return (
    <>
      <Outlet />
      <Toaster />
    </>
  )
}
