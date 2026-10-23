import { SelectField } from '@/components/shared/SelectField'
import { useUsers } from '@/hooks/useUsers'
import { roleLabel } from '@/lib/labels'

interface UserSelectProps {
  name: string
  label: string
  required: boolean
  disabled: boolean
  /** Currently assigned person, preselected. */
  current?: string | null
}

/** The people a case can be handed to: first-tier staff (the manager already sees everything). */
export function UserSelect({ name, label, required, disabled, current }: UserSelectProps) {
  const users = useUsers()
  const staff = users.status === 'success' ? users.data.filter((user) => user.role !== 'manager') : []
  const placeholder =
    users.status === 'loading' ? 'Loading people…' : users.status === 'error' ? 'Could not load people' : 'Choose a person'
  return (
    <SelectField
      name={name}
      label={label}
      required={required}
      disabled={disabled || users.status !== 'success'}
      defaultValue={current ?? ''}
      options={[
        { value: '', label: placeholder },
        ...staff.map((user) => ({ value: user.username, label: `${user.full_name} (${roleLabel[user.role]})` })),
      ]}
    />
  )
}
