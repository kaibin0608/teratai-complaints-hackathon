import { Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/shared/Button'
import { Card } from '@/components/shared/Card'
import { SelectField } from '@/components/shared/SelectField'
import { TextArea } from '@/components/shared/TextArea'
import { TextField } from '@/components/shared/TextField'
import { now } from '@/lib/clock'
import { toContractTime } from '@/lib/intake'
import { COMPLAINT_CHANNELS, type ComplaintInput } from '@/lib/types'

const newId = () => `LIVE-${String(Date.now()).slice(-5)}`

const EXAMPLE = 'Hi, I was charged twice at ShopLah Online today for RM89.90. Please refund one of them.'

interface IntakeFormProps {
  disabled: boolean
  onSubmit: (complaints: ComplaintInput[]) => void
}

/** One complaint. Defaults to the current time and a fresh ID. */
export function IntakeForm({ disabled, onSubmit }: IntakeFormProps) {
  // A new ID after each send, so the same complaint is not posted twice by accident.
  const [id, setId] = useState(newId)
  const [channel, setChannel] = useState<string>(COMPLAINT_CHANNELS[0])
  const [text, setText] = useState('')

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
    setText('')
  }

  return (
    <Card title="New complaint">
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Complaint ID" name="complaint_id" key={id} defaultValue={id} required />
          <TextField
            label="Customer ID"
            name="customer_id"
            placeholder="CUS-02394"
            pattern="[Cc][Uu][Ss]-\d{5}"
            title="CUS- followed by 5 digits"
            hint="Must be an existing customer."
            required
          />
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
        <div className="flex flex-col gap-1.5">
          <TextArea
            label="Complaint text"
            name="text"
            rows={6}
            required
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="What the customer wrote or said…"
            hint="English, Malay or mixed. Relative dates (“last Friday”) are read against the received time."
          />
          <div className="flex items-center justify-between text-xs text-secondary">
            <button type="button" onClick={() => setText(EXAMPLE)} className="font-medium text-link hover:text-link-hover">
              Use an example
            </button>
            <span className="tabular-nums">{text.length} characters</span>
          </div>
        </div>
        <div className="flex justify-end border-t border-subtle pt-4">
          <Button type="submit" variant="primary" disabled={disabled}>
            <Send size={16} aria-hidden />
            Send to the agent
          </Button>
        </div>
      </form>
    </Card>
  )
}
