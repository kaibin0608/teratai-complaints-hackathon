import { useCallback, useState } from 'react'
import { intakeApi } from '@/api/intake'
import type { ComplaintInput } from '@/lib/types'
import { useToast } from './useToast'

export type SubmissionState = 'sending' | 'received' | 'failed'

export interface Submission {
  complaint: ComplaintInput
  state: SubmissionState
  error: string | null
}

/** Sends complaints to POST /complaints and remembers each one's result (newest first). */
export function useSubmissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const { show } = useToast()

  const update = (id: string, patch: Partial<Submission>) =>
    setSubmissions((current) => current.map((s) => (s.complaint.complaint_id === id ? { ...s, ...patch } : s)))

  const submit = useCallback(async (complaints: readonly ComplaintInput[]) => {
    const ids = new Set(complaints.map((c) => c.complaint_id))
    setSubmissions((current) => [
      ...complaints.map((complaint): Submission => ({ complaint, state: 'sending', error: null })),
      ...current.filter((s) => !ids.has(s.complaint.complaint_id)),
    ])
    const accepted = await Promise.all(
      complaints.map(async (complaint) => {
        try {
          await intakeApi.submit(complaint)
          update(complaint.complaint_id, { state: 'received' })
          return true
        } catch (error) {
          update(complaint.complaint_id, { state: 'failed', error: error instanceof Error ? error.message : String(error) })
          return false
        }
      }),
    )
    const sent = accepted.filter(Boolean).length
    const failed = accepted.length - sent
    const only = complaints.length === 1 ? complaints[0]?.complaint_id : undefined
    if (failed === 0) {
      show({ tone: 'success', title: only ? `Sent ${only} to the agent` : `Sent ${sent} complaints to the agent`, description: 'Follow progress in the list on this page.' })
    } else {
      show({
        tone: 'error',
        title: only ? `${only} was not accepted` : `${failed} of ${complaints.length} complaints were not accepted`,
        description: 'The reason is next to each one in the list.',
      })
    }
  }, [show])

  return { submissions, submit }
}
