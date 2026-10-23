import { describe, expect, it } from 'vitest'
import { highlightReply } from './replyCheck'

const IDS = ['TXN-0088211']
const AMOUNTS = ['1500.00', '950.00', '550.00']
const flagged = (text: string) =>
  highlightReply(text, IDS, AMOUNTS)
    .filter((segment) => segment.flagged)
    .map((segment) => segment.text)

describe('highlightReply: the invented facts the self-check refuses', () => {
  it('marks nothing when every ID and amount is in the evidence', () => {
    expect(flagged('We reviewed TXN-0088211 (RM1,500.00). A refund of RM550.00 will follow.')).toEqual([])
  })

  it('marks an invented amount and an invented transaction ID (the judges\' demo case)', () => {
    expect(flagged('We will refund RM999.00 for TXN-0000001.')).toEqual(['RM999.00', 'TXN-0000001'])
  })

  it('reads amounts however they are written', () => {
    expect(flagged('RM 550, RM550.0, RM1,500.00 and RM1500')).toEqual([])
    expect(flagged('RM1383.2')).toEqual(['RM1383.2'])
  })

  it('leaves trailing punctuation outside the marked text', () => {
    const segments = highlightReply('Refund RM999, thanks.', IDS, AMOUNTS)
    expect(segments.find((s) => s.flagged)?.text).toBe('RM999')
  })

  it('does not mistake a cent value for a larger one', () => {
    expect(flagged('RM1,500.00')).toEqual([])
    expect(flagged('RM150.00')).toEqual(['RM150.00'])
  })

  it('keeps all the text, in order', () => {
    const text = 'Dear customer, RM999.00 and TXN-0000001 done.'
    expect(highlightReply(text, IDS, AMOUNTS).map((s) => s.text).join('')).toBe(text)
  })

  it('returns one plain segment when there is nothing to check', () => {
    expect(highlightReply('No facts here.', IDS, AMOUNTS)).toEqual([{ text: 'No facts here.', flagged: false }])
  })
})
