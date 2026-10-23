import { CircleAlert } from 'lucide-react'
import { useActionState } from 'react'
import { ApiError } from '@/api/client'
import logo from '@/assets/teratai-logo.png'
import { Button } from '@/components/shared/Button'
import { TextField } from '@/components/shared/TextField'
import { useAuth } from '@/hooks/useAuth'

interface SignInState {
  error: string | null
  /** Kept so a failed attempt doesn't clear the username field. */
  username: string
}

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
    <main className="grid min-h-dvh place-items-center bg-page p-page">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src={logo} alt="" className="mb-3 h-14 w-auto mix-blend-multiply" />
          <h1 className="text-2xl font-semibold">Teratai Bank</h1>
          <p className="mt-1 text-sm text-secondary">Complaints Ops: sign in to continue</p>
        </div>

        <form action={signIn} className="flex flex-col gap-4 rounded-card border border-default bg-card p-card shadow-card">
          {state.error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-control border border-error-200 bg-error-50 px-3 py-2 text-sm text-error-800"
            >
              <CircleAlert size={16} aria-hidden className="mt-0.5 shrink-0 text-error-500" />
              {state.error}
            </div>
          )}
          <TextField
            label="Username"
            name="username"
            autoComplete="username"
            defaultValue={state.username}
            required
            autoFocus
          />
          <TextField label="Password" name="password" type="password" autoComplete="current-password" required />
          <Button type="submit" variant="primary" disabled={pending}>
            {pending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        {import.meta.env.DEV && (
          <p className="mt-4 text-center text-xs leading-relaxed text-secondary">
            Demo users: officer1 · officer2 · fraud1 · manager1
            <br />
            Password: teratai123
          </p>
        )}
      </div>
    </main>
  )
}
