import { CircleAlert, CircleCheck, TriangleAlert } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { ApiError } from '@/api/client'
import { casesApi } from '@/api/cases'
import { Banner } from '@/components/shared/Banner'
import { Button } from '@/components/shared/Button'
import { Dialog } from '@/components/shared/Dialog'
import { SelectField } from '@/components/shared/SelectField'
import { TextArea } from '@/components/shared/TextArea'
import { TextField } from '@/components/shared/TextField'
import type { ActionKey } from '@/lib/actions'
import type { ActionBodies, CaseDetail } from '@/lib/types'
import { ACTIONS, type FieldSpec } from './actionConfig'
import { UserSelect } from './UserSelect'

interface ActionDialogProps {
  /** The action being confirmed; null keeps the dialog closed. */
  action: ActionKey | null
  detail: CaseDetail
  onClose: () => void
  /** The case changed on the server: re-fetch it. */
  onChanged: () => void
}

export function ActionDialog({ action, detail, onClose, onChanged }: ActionDialogProps) {
  return (
    <Dialog open={action !== null} title={action ? ACTIONS[action].title : ''} onClose={onClose}>
      {action && <ActionForm key={action} action={action} detail={detail} onClose={onClose} onChanged={onChanged} />}
    </Dialog>
  )
}

type FormState =
  | { status: 'idle' }
  | { status: 'pending' }
  | { status: 'error'; error: Error }
  /** edit-reply keeps the dialog open to show the self-check result. */
  | { status: 'saved'; draft: NonNullable<CaseDetail['draft_reply']> | null }

interface ActionFormProps {
  action: ActionKey
  detail: CaseDetail
  onClose: () => void
  onChanged: () => void
}

function ActionForm({ action, detail, onClose, onChanged }: ActionFormProps) {
  const spec = ACTIONS[action]
  const [state, setState] = useState<FormState>({ status: 'idle' })
  const pending = state.status === 'pending'
  const description = spec.description(detail)
  const destructive = action === 'reject' || action === 'second-tier-reject'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const body: Record<string, string> = {}
    for (const field of spec.fields(detail)) {
      const value = String(form.get(field.name) ?? '').trim()
      if (value) body[field.name] = value
    }

    setState({ status: 'pending' })
    try {
      // The field specs mirror ActionBodies; the backend validates the rest.
      const next = await casesApi.act(detail.case.complaint_id, action, body as ActionBodies[ActionKey])
      onChanged()
      if (action === 'edit-reply') setState({ status: 'saved', draft: next.draft_reply })
      else onClose()
    } catch (error) {
      const failure = error instanceof Error ? error : new Error(String(error))
      if (failure instanceof ApiError && failure.status === 409) onChanged() // the case moved on: show its new state
      setState({ status: 'error', error: failure })
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 p-card">
      {description && <p className="text-sm text-body">{description}</p>}

      {state.status === 'saved' && <SavedResult draft={state.draft} />}
      {state.status === 'error' && <FailureBanner error={state.error} />}

      {spec.fields(detail).map((field) => (
        <Field key={field.name} field={field} disabled={pending} assignedTo={detail.case.assigned_to} />
      ))}

      <div className="flex justify-end gap-2">
        <Button onClick={onClose} disabled={pending}>
          {state.status === 'saved' ? 'Close' : 'Cancel'}
        </Button>
        <Button type="submit" variant={destructive ? 'danger' : 'primary'} disabled={pending}>
          {pending ? 'Working…' : state.status === 'saved' ? 'Save again' : spec.submit}
        </Button>
      </div>
    </form>
  )
}

function Field({ field, disabled, assignedTo }: { field: FieldSpec; disabled: boolean; assignedTo: string | null }) {
  const common = { name: field.name, label: field.label, hint: field.hint, required: field.required, disabled }
  if (field.input === 'user') return <UserSelect {...common} current={assignedTo} />
  if (field.input === 'select') return <SelectField {...common} options={field.options ?? []} />
  if (field.input === 'textarea') return <TextArea {...common} rows={field.rows ?? 3} defaultValue={field.defaultValue} />
  return <TextField {...common} defaultValue={field.defaultValue} />
}

/** The backend saved the edit; show whether it passes the self-check, with the problems next to the text. */
function SavedResult({ draft }: { draft: NonNullable<CaseDetail['draft_reply']> | null }) {
  if (!draft) return null
  if (draft.self_check === 'passed') {
    return (
      <Banner tone="info" icon={CircleCheck} title="Saved: the reply passes the self-check">
        Approve will send this version.
      </Banner>
    )
  }
  return (
    <Banner tone="warning" icon={TriangleAlert} title="Saved, but the self-check flags the reply">
      Approve stays locked until it passes. Fix these, then save again:
      <ul className="mt-1 list-disc pl-4">
        {draft.problems.map((problem) => (
          <li key={problem}>{problem}</li>
        ))}
      </ul>
    </Banner>
  )
}

function FailureBanner({ error }: { error: Error }) {
  const api = error instanceof ApiError ? error : null
  return (
    <Banner tone="error" icon={CircleAlert} title={api?.limit ? 'Over your approval limit' : 'This could not be done'}>
      {api?.limit ? `${api.limit.why}. Escalate it to the manager.` : error.message}
      {api && api.problems.length > 0 && (
        <ul className="mt-1 list-disc pl-4">
          {api.problems.map((problem) => (
            <li key={problem}>{problem}</li>
          ))}
        </ul>
      )}
      {api?.status === 409 && ' The case has moved on, so this page was refreshed.'}
    </Banner>
  )
}
