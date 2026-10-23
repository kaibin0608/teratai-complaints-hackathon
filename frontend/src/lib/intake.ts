import { parseCsv } from './csv'
import type { ComplaintInput } from './types'

const FIELDS = ['complaint_id', 'customer_id', 'received_at', 'channel', 'subject', 'text'] as const
const REQUIRED: readonly (typeof FIELDS)[number][] = ['complaint_id', 'customer_id', 'received_at', 'channel', 'text']

/** A datetime-local value ("2026-09-30T10:15") → the contract's "2026-09-30 10:15". */
export const toContractTime = (value: string): string => value.trim().replace('T', ' ')

export interface ParsedIntake {
  complaints: ComplaintInput[]
  /** One message per row that cannot be sent, e.g. "Row 2: customer_id is empty". */
  errors: string[]
}

/** Parse live-round rows (`complaint_id,customer_id,received_at,channel,subject,text`); the header row is optional. */
export function parseIntakeCsv(text: string): ParsedIntake {
  const rows = parseCsv(text)
  const body = rows[0]?.[0]?.trim().toLowerCase() === 'complaint_id' ? rows.slice(1) : rows
  const complaints: ComplaintInput[] = []
  const errors: string[] = []

  body.forEach((cells, index) => {
    const label = `Row ${index + 1}`
    if (cells.length !== FIELDS.length) {
      errors.push(`${label}: expected ${FIELDS.length} columns but found ${cells.length}. Put quotes around text that contains commas.`)
      return
    }
    const complaint = Object.fromEntries(FIELDS.map((field, i) => [field, (cells[i] ?? '').trim()])) as unknown as ComplaintInput
    const missing = REQUIRED.filter((field) => complaint[field] === '')
    if (missing.length > 0) errors.push(`${label}: ${missing.join(', ')} ${missing.length === 1 ? 'is' : 'are'} empty.`)
    else complaints.push(complaint)
  })
  return { complaints, errors }
}
