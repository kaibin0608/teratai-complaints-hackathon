import { createBrowserRouter } from 'react-router'
import { AppLayout } from '@/components/layout/AppLayout'
import { HomeRedirect } from '@/components/layout/HomeRedirect'
import { ProtectedRoute } from '@/components/layout/ProtectedRoute'
import { PublicOnlyRoute } from '@/components/layout/PublicOnlyRoute'
import { paths } from '@/lib/paths'
import { AuditLog } from '@/pages/AuditLog'
import { CaseDetail } from '@/pages/CaseDetail'
import { Cases } from '@/pages/Cases'
import { FraudWorkbench } from '@/pages/FraudWorkbench'
import { Intake } from '@/pages/Intake'
import { Login } from '@/pages/Login'
import { ManagerConsole } from '@/pages/ManagerConsole'
import { OfficerDesk } from '@/pages/OfficerDesk'
import { Policy } from '@/pages/Policy'

/**
 * URL → page, and which roles may open it. The manager sees both queues (PLAN.md Roles).
 * Keep role rules in step with components/layout/navigation.ts.
 */
export const router = createBrowserRouter([
  {
    element: <PublicOnlyRoute />,
    children: [{ path: paths.login, element: <Login /> }],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: paths.intake, element: <Intake /> },
          { path: '/cases/:complaintId', element: <CaseDetail /> },
          {
            element: <ProtectedRoute roles={['officer', 'manager']} />,
            children: [{ path: paths.officer, element: <OfficerDesk /> }],
          },
          {
            element: <ProtectedRoute roles={['fraud', 'manager']} />,
            children: [{ path: paths.fraud, element: <FraudWorkbench /> }],
          },
          {
            element: <ProtectedRoute roles={['manager']} />,
            children: [
              { path: paths.manager, element: <ManagerConsole /> },
              { path: paths.cases, element: <Cases /> },
              { path: paths.audit, element: <AuditLog /> },
              { path: paths.policy, element: <Policy /> },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <HomeRedirect /> },
])
