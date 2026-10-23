import type { Money } from './types'

export interface ReplySegment {
  text: string
  /** A transaction ID or amount that is not in the evidence: the invented facts the self-check refuses. */
  flagged: boolean
}

/** A transaction ID, or an RM amount ("RM1,500.00", "RM 550", "RM1383.2"); a trailing comma or full stop is not part of it. */
const FACT = /TXN-\d{7}|RM\s?\d+(?:,\d{3})*(?:\.\d{1,2})?/g

/** "RM 1,383.2" → "1383.20" (string maths only: no floats). */
function normaliseAmount(raw: string): string {
  const [whole = '0', fraction = ''] = raw.replace(/^RM\s?/, '').replace(/,/g, '').split('.')
  return `${whole}.${fraction.padEnd(2, '0')}`
}

/**
 * Split a reply into plain and flagged segments for display. This only marks text for the reader:
 * the authoritative check is the backend's (`reply.self_check`), never this.
 */
export function highlightReply(
  text: string,
  allowedTxnIds: readonly string[],
  allowedAmounts: readonly Money[],
): ReplySegment[] {
  const ids = new Set(allowedTxnIds)
  const amounts = new Set(allowedAmounts.map(normaliseAmount))
  const segments: ReplySegment[] = []
  let cursor = 0
  for (const match of text.matchAll(FACT)) {
    const found = match[0]
    const flagged = found.startsWith('TXN-') ? !ids.has(found) : !amounts.has(normaliseAmount(found))
    if (match.index > cursor) segments.push({ text: text.slice(cursor, match.index), flagged: false })
    segments.push({ text: found, flagged })
    cursor = match.index + found.length
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), flagged: false })
  return segments
}
