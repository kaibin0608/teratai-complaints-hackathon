import { Link } from 'react-router'
import { Card } from '@/components/shared/Card'
import { useNameOf } from '@/hooks/useNameOf'
import { useOpenWork } from '@/hooks/useOpenWork'
import { useUsers } from '@/hooks/useUsers'
import { now, mytToMs } from '@/lib/clock'
import { cx } from '@/lib/cx'
import { roleLabel } from '@/lib/labels'
import { paths } from '@/lib/paths'
import { summariseWork } from '@/lib/workload'

/** Who holds how much of the open work. Unassigned cases are the manager's to hand out (from the case page). */
export function TeamWorkload() {
  const work = useOpenWork()
  const users = useUsers()
  const nameOf = useNameOf()
  if (work.status !== 'success' || users.status !== 'success') return <Card title="Team workload">{null}</Card>

  const { byPerson } = summariseWork(work.data.items, mytToMs(now()))
  const staff = users.data.filter((user) => user.role !== 'manager')
  const unassigned = byPerson.get(null)
  const head = 'px-cell-x py-cell-y font-medium'

  return (
    <Card title="Team workload" aside={<span className="text-xs text-secondary">open cases</span>}>
      <div className="-mx-card -my-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] tracking-wide text-secondary uppercase">
            <tr>
              <th scope="col" className={head}>Person</th>
              <th scope="col" className={cx(head, 'text-right')}>Open</th>
              <th scope="col" className={cx(head, 'text-right')}>Overdue</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {staff.map((user) => {
              const load = byPerson.get(user.username)
              return (
                <tr key={user.username}>
                  <td className="px-cell-x py-cell-y">
                    <span className="font-medium text-primary">{nameOf(user.username)}</span>
                    <span className="ml-2 text-xs text-secondary">{roleLabel[user.role]}</span>
                  </td>
                  <td className="px-cell-x py-cell-y text-right tabular-nums">{load?.open ?? 0}</td>
                  <td className={cx('px-cell-x py-cell-y text-right tabular-nums', load?.overdue ? 'font-medium text-error-700' : 'text-secondary')}>{load?.overdue ?? 0}</td>
                </tr>
              )
            })}
            <tr className="bg-neutral-25">
              <td className="px-cell-x py-cell-y">
                <Link to={`${paths.cases}?assigned=none`} className="font-medium text-link hover:text-link-hover">
                  Not assigned to anyone
                </Link>
              </td>
              <td className="px-cell-x py-cell-y text-right tabular-nums">{unassigned?.open ?? 0}</td>
              <td className={cx('px-cell-x py-cell-y text-right tabular-nums', unassigned?.overdue ? 'font-medium text-error-700' : 'text-secondary')}>{unassigned?.overdue ?? 0}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  )
}
