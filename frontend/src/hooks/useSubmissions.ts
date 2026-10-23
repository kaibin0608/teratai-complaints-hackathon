import { useCallback, useState } from 'react'
import { intakeApi } from '@/api/intake'
import type { ComplaintInput } from '@/lib/types'

export type SubmissionState = 'sending' | 'received' | 'failed'

export interface Submission {
  complaint: ComplaintInput
  state: SubmissionState
  error: string | null
}

/** Sends complaints to POST /complaints and remembers each one's result (newest first). */
export function useSubmissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([])

  const update = (id: string, patch: Partial<Submission>) =>
    setSubmissions((current) => current.map((s) => (s.complaint.complaint_id === id ? { ...s, ...patch } : s)))

  const submit = useCallback(async (complaints: readonly ComplaintInput[]) => {
    const ids = new Set(complaints.map((c) => c.complaint_id))
    setSubmissions((current) => [
      ...complaints.map((complaint): Submission => ({ complaint, state: 'sending', error: null })),
      ...current.filter((s) => !ids.has(s.complaint.complaint_id)),
    ])
    await Promise.all(
      complaints.map(async (complaint) => {
        try {
          await intakeApi.submit(complaint)
          update(complaint.complaint_id, { state: 'received' })
        } catch (error) {
          update(complaint.complaint_id, { state: 'failed', error: error instanceof Error ? error.message : String(error) })
        }
      }),
    )
  }, [])

  return { submissions, submit }
}
