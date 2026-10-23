import { useState } from 'react'
import { Button } from '@/components/shared/Button'
import { TextArea } from '@/components/shared/TextArea'
import { parseIntakeCsv } from '@/lib/intake'
import type { ComplaintInput } from '@/lib/types'

const EXAMPLE = `complaint_id,customer_id,received_at,channel,subject,text
LIVE-07,CUS-01234,2026-09-30 10:15,App chat,,"Hi, I was charged twice at ShopLah Online today for RM89.90..."`

interface IntakePasteProps {
  disabled: boolean
  onSubmit: (complaints: ComplaintInput[]) => void
}

/** The live-round format: one or more rows of `complaint_id,customer_id,received_at,channel,subject,text`. */
export function IntakePaste({ disabled, onSubmit }: IntakePasteProps) {
  const [text, setText] = useState('')
  const { complaints, errors } = parseIntakeCsv(text)
  const empty = text.trim() === ''

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <TextArea
        label="CSV rows"
        rows={7}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={EXAMPLE}
        hint="The header row is optional. Put quotes around text that contains commas."
        spellCheck={false}
      />

      {!empty && errors.length > 0 && (
        <ul className="list-disc pl-5 text-sm text-error-700">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      {complaints.length > 0 && (
        <p className="text-sm text-body">
          Ready to send: {complaints.map((c) => c.complaint_id).join(', ')} ({complaints.length} complaint
          {complaints.length === 1 ? '' : 's'}).
        </p>
      )}

      <div>
        <Button
          variant="primary"
          disabled={disabled || complaints.length === 0 || errors.length > 0}
          onClick={() => {
            onSubmit(complaints)
            setText('')
          }}
        >
          Send {complaints.length > 1 ? `${complaints.length} complaints` : 'to the agent'}
        </Button>
      </div>
    </div>
  )
}
