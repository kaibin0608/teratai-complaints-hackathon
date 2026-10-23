import { Search, X } from 'lucide-react'
import { useEffect, useEffectEvent, useState, type ComponentProps } from 'react'
import { controlClass } from '@/components/shared/FieldShell'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { cx } from '@/lib/cx'
import { categoryLabel, holdReasonLabel, workflowLabel } from '@/lib/labels'
import { CATEGORIES, HOLD_REASONS, PRIORITIES, WORKFLOWS, type CaseList } from '@/lib/types'
import { activeFilters, type Assigned, type QueueParams } from './queueParams'

interface QueueFiltersProps {
  params: QueueParams
  /** Counts per workflow over everything the user can see: shown in the workflow menu. */
  workflowCounts: CaseList['workflow_counts'] | undefined
  /** "Changed by people" is an audit view: only the manager gets it. */
  showChanged: boolean
  onChange: (key: keyof QueueParams, value: string | boolean | null) => void
  onClear: () => void
}

/** Search and filters for a queue. Everything is kept in the URL by the caller. */
export function QueueFilters({ params, workflowCounts, showChanged, onChange, onClear }: QueueFiltersProps) {
  // The box keeps its own text so typing never lags; the URL (and the request) follow after a pause.
  const [text, setText] = useState(params.q)
  const settled = useDebouncedValue(text, 300)
  const writeSearch = useEffectEvent((value: string) => {
    if (value !== params.q) onChange('q', value)
  })
  useEffect(() => writeSearch(settled), [settled])

  const active = activeFilters(params)
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative w-72">
        <Search size={14} aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-secondary" />
        <input
          type="search"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Search case, customer, subject"
          aria-label="Search cases"
          className={cx('h-8 w-full pl-8', controlClass)}
        />
      </div>

      <Select label="Category" value={params.category} onChange={(v) => onChange('category', v)} options={CATEGORIES.map((v) => [v, categoryLabel[v]])} />
      <Select label="Priority" value={params.priority} onChange={(v) => onChange('priority', v)} options={PRIORITIES.map((v) => [v, v])} />
      <Select
        label="Hold"
        value={params.hold}
        onChange={(v) => onChange('hold', v)}
        options={[['none', 'Not held'], ...HOLD_REASONS.map((v) => [v, holdReasonLabel[v]] as const)]}
      />
      <Select
        label="Workflow"
        value={params.workflow}
        onChange={(v) => onChange('workflow', v)}
        options={WORKFLOWS.map((v) => [v, `${workflowLabel[v]}${workflowCounts ? ` (${workflowCounts[v]})` : ''}`])}
      />
      <Select
        label="Assigned"
        value={params.assigned}
        onChange={(v) => onChange('assigned', v as Assigned | null)}
        options={[
          ['me', 'To me'],
          ['none', 'Unassigned'],
        ]}
      />

      <Check checked={params.sensitive} onChange={(v) => onChange('sensitive', v)} label="Sensitive only" />
      {showChanged && <Check checked={params.changed} onChange={(v) => onChange('changed', v)} label="Changed by people" />}

      {active > 0 && (
        <button
          type="button"
          onClick={() => {
            setText('')
            onClear()
          }}
          className="flex items-center gap-1 text-xs font-medium text-link hover:text-link-hover"
        >
          <X size={12} aria-hidden />
          Clear {active} filter{active === 1 ? '' : 's'}
        </button>
      )}
    </div>
  )
}

interface SelectProps {
  label: string
  value: string | null
  onChange: (value: string | null) => void
  options: readonly (readonly [string, string])[]
}

/** A compact filter menu whose first entry ("Category: any") clears it. */
function Select({ label, value, onChange, options }: SelectProps) {
  const props: ComponentProps<'select'> = {
    'aria-label': label,
    value: value ?? '',
    onChange: (event) => onChange(event.target.value || null),
  }
  return (
    <select {...props} className={cx('h-8 pr-6 text-xs', controlClass, value && 'border-brand-600 bg-brand-50 text-brand-800')}>
      <option value="">{label}: any</option>
      {options.map(([optionValue, optionLabel]) => (
        <option key={optionValue} value={optionValue}>
          {optionLabel}
        </option>
      ))}
    </select>
  )
}

function Check({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <label className="flex h-8 items-center gap-1.5 text-xs text-body">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="size-3.5 accent-brand-600" />
      {label}
    </label>
  )
}
