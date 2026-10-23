import { describe, expect, it } from 'vitest'
import { officer } from '@/test/fixtures'
import { makeNameOf } from './people'

describe('makeNameOf', () => {
  const nameOf = makeNameOf([officer])

  it('shows a known person by full name', () => {
    expect(nameOf(officer.username)).toBe(officer.full_name)
  })

  it('shows the agent as Agent', () => {
    expect(nameOf('agent')).toBe('Agent')
  })

  it('never shows a raw username for someone it cannot look up', () => {
    expect(nameOf('fraud2')).toBe('Fraud 2')
  })
})
