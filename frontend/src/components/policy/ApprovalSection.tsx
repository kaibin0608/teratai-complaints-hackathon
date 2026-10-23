import { CircleAlert, LoaderCircle } from 'lucide-react'
import { Card } from '@/components/shared/Card'
import { StatusMessage } from '@/components/shared/StatusMessage'
import { useUsers } from '@/hooks/useUsers'
import { formatMoney } from '@/lib/format'
import { roleLabel } from '@/lib/labels'
import { parameterValue, type Policy } from '@/lib/policy'
import type { Role, User } from '@/lib/types'
import { PolicySection } from './PolicySection'
import { PolicyTable, type Column } from './PolicyTable'

/** What each role's limit is measured on (UI_API.md, "Limit and sensitivity"). */
const MEASURED_ON: Record<Role, string> = {
  officer: 'The refund',
  fraud: 'The disputed transaction',
  manager: 'No limit',
}

const USER_COLUMNS: readonly Column<User>[] = [
  { head: 'Person', render: (user) => user.full_name },
  { head: 'Role', render: (user) => roleLabel[user.role] },
  { head: 'Approval limit', render: (user) => <span className="tabular-nums">{user.approval_limit_myr === null ? 'None' : formatMoney(user.approval_limit_myr)}</span> },
  { head: 'Measured on', render: (user) => MEASURED_ON[user.role] },
]

/** Who can approve what. The limits belong to the platform, not the bank's policy files, so they come from the users. */
export function ApprovalSection({ policy }: { policy: Policy }) {
  const users = useUsers()
  const limit = parameterValue(policy, 'AUTO_REFUND_LIMIT_MYR')
  const age = parameterValue(policy, 'VULNERABLE_AGE')

  return (
    <PolicySection
      id="approval"
      title="Approval and escalation"
      description="Who may decide a case, and when it must go to the manager. The backend enforces these; the screens only show them."
    >
      <Card title="Approval limits">
        {users.status === 'loading' && <StatusMessage busy icon={LoaderCircle} title="Loading…" />}
        {users.status === 'error' && (
          <StatusMessage icon={CircleAlert} title="Could not load the approval limits">
            {users.error.message}
          </StatusMessage>
        )}
        {users.status === 'success' && (
          <PolicyTable columns={USER_COLUMNS} rows={users.data} rowKey={(user) => user.username} />
        )}
      </Card>

      <Card title="The rules">
        <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-body">
          <li>
            Every decline, and every refund over <strong className="text-primary">{limit}</strong>, waits for an officer before anything reaches the customer. Fraud
            investigations go to the fraud team. Everything else is sent automatically.
          </li>
          <li>
            An officer cannot approve a refund over their limit, and a fraud analyst cannot record an outcome when the disputed transaction is over theirs. Either
            escalates the case to the manager.
          </li>
          <li>
            A customer aged <strong className="text-primary">{age}</strong> or over on the day the complaint arrives is always sensitive: the priority goes up one
            level, and the case has to go to the manager whatever the amount.
          </li>
          <li>Anyone can flag a case as sensitive, with a reason; it then needs the manager too.</li>
          <li>The manager has no limit and decides every escalated case. Nothing escalated is sent until they do.</li>
          <li>Refunds and messages are simulated: approving records them in an outbox and nothing really leaves the system.</li>
        </ul>
      </Card>
    </PolicySection>
  )
}
