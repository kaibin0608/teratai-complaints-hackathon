import type { ReactNode } from 'react'

export interface Column<T> {
  head: string
  render: (row: T) => ReactNode
}

interface PolicyTableProps<T> {
  columns: readonly Column<T>[]
  rows: readonly T[]
  rowKey: (row: T) => string
}

/** A plain read-only table inside a card: one column per `columns` entry, one row per item. */
export function PolicyTable<T>({ columns, rows, rowKey }: PolicyTableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-card border border-default bg-card">
      <table className="w-full text-sm">
        <thead className="bg-subtle text-left text-[11px] tracking-wide text-secondary uppercase">
          <tr>
            {columns.map(({ head }) => (
              <th key={head} scope="col" className="px-cell-x py-cell-y font-medium whitespace-nowrap">
                {head}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {rows.map((row) => (
            <tr key={rowKey(row)} className="align-top">
              {columns.map(({ head, render }) => (
                <td key={head} className="px-cell-x py-cell-y text-body first:font-medium first:text-primary">
                  {render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
