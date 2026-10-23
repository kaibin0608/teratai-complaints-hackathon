import { Bot, CircleAlert, Eye, EyeOff, LockKeyhole, ScrollText, ShieldCheck, type LucideIcon } from 'lucide-react'
import { useActionState, useId, useState } from 'react'
import { ApiError } from '@/api/client'
import logo from '@/assets/teratai-logo.png'
import { Button } from '@/components/shared/Button'
import { controlClass, FieldShell } from '@/components/shared/FieldShell'
import { TextField } from '@/components/shared/TextField'
import { useAuth } from '@/hooks/useAuth'

interface SignInState {
  error: string | null
  /** Kept so a failed attempt doesn't clear the username field. */
  username: string
}

/** What the platform does, in the three things staff most need to trust. */
const POINTS: readonly { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: Bot,
    title: 'The agent drafts, people decide',
    text: 'It reads each complaint, finds the transaction and proposes a decision and a reply. A person approves anything that moves money.',
  },
  {
    icon: ShieldCheck,
    title: 'Money and rules run in code',
    text: 'Refund amounts, approval limits and the check on every reply are calculated by code, never guessed by a model.',
  },
  {
    icon: ScrollText,
    title: 'Everything is on the record',
    text: 'Each action is written to an append-only audit log, so any decision can be traced afterwards.',
  },
]

/** PLAN.md §3.2. On success PublicOnlyRoute redirects by role. */
export function Login() {
  const { login } = useAuth()
  const [state, signIn, pending] = useActionState<SignInState, FormData>(
    async (_previous, form) => {
      const username = String(form.get('username') ?? '').trim()
      try {
        await login(username, String(form.get('password') ?? ''))
        return { error: null, username }
      } catch (error) {
        return { error: error instanceof ApiError ? error.message : 'Sign-in failed. Please try again.', username }
      }
    },
    { error: null, username: '' },
  )

  return (
    <main className="grid min-h-dvh bg-card lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <section className="flex flex-col px-page py-8 sm:px-12">
        <div className="flex items-center gap-2.5">
          {/* multiply drops the logo's near-white background into the page colour */}
          <img src={logo} alt="Teratai Bank" className="h-9 w-auto mix-blend-multiply" />
          <span className="h-5 w-px bg-neutral-200" aria-hidden />
          <span className="text-sm font-medium text-secondary">Complaints Ops</span>
        </div>

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <h1 className="text-3xl font-semibold">Sign in</h1>
          <p className="mt-2 text-sm text-secondary">Use your staff account to open your queue.</p>

          <form action={signIn} className="mt-8 flex flex-col gap-4">
            {state.error && (
              <div role="alert" className="flex items-start gap-2 rounded-control border border-error-200 bg-error-50 px-3 py-2 text-sm text-error-800">
                <CircleAlert size={16} aria-hidden className="mt-0.5 shrink-0 text-error-500" />
                {state.error}
              </div>
            )}
            <TextField label="Username" name="username" autoComplete="username" defaultValue={state.username} required autoFocus />
            <PasswordField />
            <Button type="submit" variant="primary" disabled={pending} className="mt-2 h-10">
              {pending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>

          {import.meta.env.DEV && (
            <p className="mt-6 rounded-control bg-subtle px-3 py-2 text-center text-xs leading-relaxed text-secondary">
              Demo users: officer1 · officer2 · fraud1 · manager1
              <br />
              Password: teratai123
            </p>
          )}
        </div>

        <p className="flex items-center gap-1.5 text-xs text-secondary">
          <LockKeyhole size={12} aria-hidden />
          Authorised staff only. Your activity is logged.
        </p>
      </section>

      <aside className="relative hidden flex-col justify-center overflow-hidden bg-linear-to-br from-brand-50 via-neutral-25 to-aubergine-100 px-16 py-12 lg:flex">
        <div aria-hidden className="pointer-events-none absolute -top-24 -right-24 size-96 rounded-full bg-brand-200/50 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-32 -left-20 size-96 rounded-full bg-aubergine-200/60 blur-3xl" />

        <div className="relative max-w-lg">
          <p className="text-xs font-medium tracking-wide text-brand-700 uppercase">Complaints operations</p>
          <h2 className="mt-3 text-3xl leading-tight font-semibold">Resolve every complaint quickly, and be able to show why.</h2>
          <ul className="mt-10 flex flex-col gap-6">
            {POINTS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-card border border-brand-100 bg-card text-brand-600">
                  <Icon size={20} aria-hidden />
                </span>
                <div>
                  <h3 className="text-sm font-semibold">{title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-body">{text}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </main>
  )
}

/** Password with a show/hide toggle, so a mistyped one can be checked before it fails. */
function PasswordField() {
  const id = useId()
  const [visible, setVisible] = useState(false)
  const Icon = visible ? EyeOff : Eye
  return (
    <FieldShell id={id} label="Password">
      <div className="relative">
        <input
          id={id}
          name="password"
          type={visible ? 'text' : 'password'}
          autoComplete="current-password"
          required
          className={`h-9 w-full pr-10 ${controlClass}`}
        />
        <button
          type="button"
          onClick={() => setVisible((value) => !value)}
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          className="absolute top-1/2 right-1.5 grid size-7 -translate-y-1/2 place-items-center rounded-control text-secondary hover:bg-neutral-100 hover:text-primary"
        >
          <Icon size={16} aria-hidden />
        </button>
      </div>
    </FieldShell>
  )
}
