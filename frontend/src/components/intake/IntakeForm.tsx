import { useState, type FormEvent } from 'react'
import { Button } from '@/components/shared/Button'
import { SelectField } from '@/components/shared/SelectField'
import { TextArea } from '@/components/shared/TextArea'
import { TextField } from '@/components/shared/TextField'
import { now } from '@/lib/clock'
import { toContractTime } from '@/lib/intake'
import { COMPLAINT_CHANNELS, type ComplaintInput } from '@/lib/types'

const newId = () => `LIVE-${String(Date.now()).slice(-5)}`

interface IntakeFormProps {
  disabled: boolean
  onSubmit: (complaints: ComplaintInput[]) => void
}

/** One complaint. Defaults to the current time and a fresh ID. */
export function IntakeForm({ disabled, onSubmit }: IntakeFormProps) {
  // A new ID after each send, so the same complaint is not posted twice by accident.
  const [id, setId] = useState(newId)
  const [channel, setChannel] = useState<string>(COMPLAINT_CHANNELS[0])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const value = (name: string) => String(form.get(name) ?? '').trim()
    onSubmit([
      {
        complaint_id: value('complaint_id'),
        customer_id: value('customer_id').toUpperCase(),
        received_at: toContractTime(value('received_at')),
        channel: value('channel'),
        subject: channel === 'Email' ? value('subject') : '',
        text: value('text'),
      },
    ])
    setId(newId())
  }

  return (
    <form onSubmit={submit} className="flex max-w-2xl flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField label="Complaint ID" name="complaint_id" key={id} defaultValue={id} required />
        <TextField label="Customer ID" name="customer_id" placeholder="CUS-02394" pattern="[Cc][Uu][Ss]-\d{5}" title="CUS- followed by 5 digits" required />
        <TextField label="Received at" name="received_at" type="datetime-local" defaultValue={now().slice(0, 16)} required />
        <SelectField
          label="Channel"
          name="channel"
          value={channel}
          onChange={(event) => setChannel(event.target.value)}
          options={COMPLAINT_CHANNELS.map((value) => ({ value, label: value }))}
        />
      </div>
      {channel === 'Email' && <TextField label="Subject" name="subject" required={false} />}
      <TextArea
        label="Complaint text"
        name="text"
        rows={5}
        required
        placeholder="Hi, I was charged twice at ShopLah Online today for RM89.90…"
        hint="English, Malay or mixed. Relative dates (“last Friday”) are read against the received time."
      />
      <div>
        <Button type="submit" variant="primary" disabled={disabled}>
          Send to the agent
        </Button>
      </div>
    </form>
  )
}
