import type { AuditEvent } from './types'

/** Audit actions (UI_API.md, platform actions) in plain words. Unknown actions fall back to the name itself. */
const ACTION_LABEL: Record<string, string> = {
  ingest: 'Complaint received',
  agent_run: 'Agent decided',
  approve: 'Approved',
  edit_approve: 'Edited and approved',
  edit_approve_refused: 'Edited reply refused by the self-check',
  edit_reply: 'Reply edited',
  reject: 'Rejected',
  send_back: 'Sent back to the agent',
  send_back_failed: 'Send back failed',
  escalate: 'Escalated to the manager',
  flag_sensitive: 'Flagged sensitive',
  second_tier_approve: 'Manager approved',
  second_tier_reject: 'Manager rejected',
  reassign: 'Reassigned',
  acknowledge: 'Acknowledged: holding reply sent',
  investigate: 'Investigation logged',
  record_outcome: 'Outcome recorded',
}

const humanise = (action: string) => {
  const words = action.replace(/_/g, ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}


export interface EventSummary {
  title: string
  /** The reason or note a person gave, or the agent's route and hold. */
  note: string | null
  /** Self-check problems of a refused edit. */
  problems: string[]
}

const text = (value: unknown): string | null => (typeof value === 'string' && value.trim() ? value : null)

export function describeEvent(event: AuditEvent): EventSummary {
  const detail = event.detail ?? {}
  const problems = Array.isArray(detail.problems) ? detail.problems.filter((p): p is string => typeof p === 'string') : []
  const agentRoute = event.action === 'agent_run' ? [text(detail.route), text(detail.hold_reason)].filter(Boolean).join(' · ') : null
  return {
    title: ACTION_LABEL[event.action] ?? humanise(event.action),
    note: text(detail.reason) ?? text(detail.note) ?? text(detail.error) ?? (agentRoute || null),
    problems,
  }
}
