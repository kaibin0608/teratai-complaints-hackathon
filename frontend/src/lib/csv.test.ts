import { describe, expect, it } from 'vitest'
import { parseCsv, toCsv } from './csv'
import { parseIntakeCsv, toContractTime } from './intake'

describe('parseCsv', () => {
  it('reads quoted cells with commas, doubled quotes and line breaks', () => {
    expect(parseCsv('a,"b, c","say ""hi""","line\nbreak"')).toEqual([['a', 'b, c', 'say "hi"', 'line\nbreak']])
  })

  it('accepts CRLF and skips blank lines', () => {
    expect(parseCsv('a,b\r\n\r\nc,d\r\n')).toEqual([
      ['a', 'b'],
      ['c', 'd'],
    ])
  })

  it('round-trips through toCsv, including awkward text', () => {
    const rows = [['id', 'text'], ['1', 'He said "no",\nthen left.'], ['2', '']]
    expect(parseCsv(toCsv(rows))).toEqual(rows)
  })
})

describe('parseIntakeCsv (the live-round format)', () => {
  const header = 'complaint_id,customer_id,received_at,channel,subject,text'

  it("reads the README's example, with an empty subject", () => {
    const row = 'LIVE-07,CUS-01234,2026-09-30 10:15,App chat,,"Hi, I was charged twice at ShopLah Online today for RM89.90..."'
    const { complaints, errors } = parseIntakeCsv(`${header}\n${row}`)
    expect(errors).toEqual([])
    expect(complaints).toEqual([
      {
        complaint_id: 'LIVE-07',
        customer_id: 'CUS-01234',
        received_at: '2026-09-30 10:15',
        channel: 'App chat',
        subject: '',
        text: 'Hi, I was charged twice at ShopLah Online today for RM89.90...',
      },
    ])
  })

  it('does not need the header row, and reads several rows', () => {
    const { complaints } = parseIntakeCsv('A-1,CUS-00001,2026-09-30 09:00,Email,ATM,one\nA-2,CUS-00002,2026-09-30 09:05,App chat,,two')
    expect(complaints.map((c) => c.complaint_id)).toEqual(['A-1', 'A-2'])
  })

  it('explains the common mistake of an unquoted comma', () => {
    const { complaints, errors } = parseIntakeCsv('A-1,CUS-00001,2026-09-30 10:00,App chat,,Hi, I was charged twice')
    expect(complaints).toEqual([])
    expect(errors[0]).toMatch(/expected 6 columns but found 7/)
    expect(errors[0]).toMatch(/quotes/)
  })

  it('names the empty required fields', () => {
    const { errors } = parseIntakeCsv('A-1,,2026-09-30 10:00,App chat,,hello')
    expect(errors).toEqual(['Row 1: customer_id is empty.'])
  })

  it('sends nothing for empty input', () => {
    expect(parseIntakeCsv('')).toEqual({ complaints: [], errors: [] })
  })
})

describe('toContractTime', () => {
  it('turns a datetime-local value into the contract format', () => {
    expect(toContractTime('2026-09-30T10:15')).toBe('2026-09-30 10:15')
  })
})
