import {
  CATEGORIES,
  HOLD_REASONS,
  PRIORITIES,
  WORKFLOWS,
  type CaseListQuery,
  type Category,
  type HoldReason,
  type Priority,
  type Queue,
  type Workflow,
} from '@/lib/types'

export type Sort = 'priority' | 'recent'
export type Assigned = 'me' | 'none'

/** What the queue shows, as the URL holds it (`?queue=approved&category=FEE_DISPUTE&q=aisyah`). */
export interface QueueParams {
  queue: Queue
  sort: Sort
  q: string
  category: Category | null
  priority: Priority | null
  /** 'none' = cases with no hold. */
  hold: HoldReason | 'none' | null
  workflow: Workflow | null
  assigned: Assigned | null
  sensitive: boolean
  /** Only cases where people changed the agent's decision or reply. */
  changed: boolean
}

const pick = <T extends string>(value: string | null, allowed: readonly T[]): T | null =>
  allowed.includes(value as T) ? (value as T) : null

export function readParams(params: URLSearchParams, tabs: readonly Queue[]): QueueParams {
  const queue = params.get('queue') as Queue | null
  return {
    queue: queue && tabs.includes(queue) ? queue : tabs[0]!,
    sort: params.get('sort') === 'recent' ? 'recent' : 'priority',
    q: params.get('q') ?? '',
    category: pick(params.get('category'), CATEGORIES),
    priority: pick(params.get('priority'), PRIORITIES),
    hold: pick(params.get('hold'), [...HOLD_REASONS, 'none'] as const),
    workflow: pick(params.get('workflow'), WORKFLOWS),
    assigned: pick(params.get('assigned'), ['me', 'none'] as const),
    sensitive: params.get('sensitive') === '1',
    changed: params.get('changed') === '1',
  }
}

/** Write one change into the URL, dropping empty values so links stay short. */
export function withParam(current: URLSearchParams, key: keyof QueueParams, value: string | boolean | null): URLSearchParams {
  const next = new URLSearchParams(current)
  if (value === null || value === '' || value === false) next.delete(key)
  else next.set(key, value === true ? '1' : value)
  return next
}

/** Number of filters that narrow the list (the tab and sort do not count). */
export const activeFilters = (p: QueueParams): number =>
  [p.q.trim(), p.category, p.priority, p.hold, p.workflow, p.assigned, p.sensitive || null, p.changed || null].filter(Boolean).length

export function toQuery(p: QueueParams, limit: number): CaseListQuery {
  return {
    queue: p.queue,
    sort: p.sort,
    limit,
    q: p.q.trim() || undefined,
    category: p.category ?? undefined,
    priority: p.priority ?? undefined,
    hold_reason: p.hold ?? undefined,
    workflow: p.workflow ?? undefined,
    assigned_to: p.assigned ?? undefined,
    sensitive: p.sensitive || undefined,
    overridden: p.changed || undefined,
  }
}
