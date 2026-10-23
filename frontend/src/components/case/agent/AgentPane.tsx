import { Bot, LoaderCircle, Send } from 'lucide-react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ChatError, chatApi } from '@/api/chat'
import { controlClass } from '@/components/shared/FieldShell'
import { useAuth } from '@/hooks/useAuth'
import { useChatHistory } from '@/hooks/useChatHistory'
import { suggestionsFor } from '@/lib/briefing'
import { cx } from '@/lib/cx'
import type { CaseDetail } from '@/lib/types'
import { BriefingMessage } from './BriefingMessage'

/**
 * The centre of the case page: the agent briefs you on its work, then you can ask it anything about the case.
 * It is read-only (answers come from the stored facts and the policy files); the buttons below the page are what act.
 */
export function AgentPane({ detail }: { detail: CaseDetail }) {
  const auth = useAuth()
  const complaintId = detail.case.complaint_id
  const owner = auth.status === 'signed_in' ? auth.user.username : ''
  const [turns, setTurns] = useChatHistory(owner, complaintId)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const end = useRef<HTMLDivElement>(null)

  // Keep the newest message in view as the conversation grows.
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [turns.length, busy])

  async function ask(question: string) {
    const text = question.trim()
    if (!text || busy) return
    const history = turns
    setBusy(true)
    setError(null)
    setDraft('')
    setTurns([...history, { role: 'user', content: text }])
    try {
      const { answer } = await chatApi.ask({ question: text, complaint_id: complaintId, history })
      setTurns([...history, { role: 'user', content: text }, { role: 'assistant', content: answer }])
    } catch (err) {
      setTurns(history)
      setDraft(text)
      setError(err instanceof ChatError ? err.message : 'The assistant could not answer. Try again.')
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void ask(draft)
  }

  return (
    <section aria-label="The agent" className="flex min-h-[28rem] flex-col rounded-card border border-default bg-card xl:h-full xl:min-h-0">
      <header className="flex items-center gap-2.5 border-b border-subtle px-card py-2.5">
        <Avatar />
        <div className="leading-tight">
          <h2 className="text-sm font-semibold">Agent</h2>
          <p className="text-xs text-secondary">Explains its work. Read-only: it can’t approve or send anything.</p>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-card py-4">
        <ol aria-live="polite" className="flex flex-col gap-4">
          <Message from="agent">
            <BriefingMessage detail={detail} />
          </Message>
          {turns.map((turn, index) => (
            <Message key={index} from={turn.role === 'user' ? 'you' : 'agent'}>
              <p className="text-sm leading-relaxed whitespace-pre-wrap [overflow-wrap:anywhere]">{turn.content}</p>
            </Message>
          ))}
          {busy && (
            <li role="status" className="flex items-center gap-2 pl-10 text-sm text-secondary">
              <LoaderCircle size={14} aria-hidden className="animate-spin" /> Thinking…
            </li>
          )}
        </ol>
        <div ref={end} />
      </div>

      <div className="border-t border-subtle px-card py-3">
        <div className="mb-2 flex flex-wrap gap-1.5">
          {suggestionsFor(detail).map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              disabled={busy}
              onClick={() => void ask(suggestion)}
              className="rounded-badge border border-default bg-card px-2.5 py-1 text-xs text-body transition-colors hover:bg-subtle disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>
        {error && <p className="mb-2 text-sm text-error-700">{error}</p>}
        <form onSubmit={onSubmit} className="flex items-end gap-2">
          <label htmlFor={`chat-${complaintId}`} className="sr-only">
            Ask the agent about this case
          </label>
          <textarea
            id={`chat-${complaintId}`}
            rows={2}
            maxLength={1000}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void ask(draft)
              }
            }}
            placeholder="Ask why, what the evidence shows, or who can approve…"
            className={cx('min-w-0 flex-1 resize-none py-2 leading-relaxed', controlClass)}
            disabled={busy}
          />
          <button
            type="submit"
            disabled={busy || !draft.trim()}
            aria-label="Ask"
            className="grid size-10 shrink-0 place-items-center rounded-control bg-brand-600 text-inverse transition-colors hover:bg-brand-700 disabled:bg-neutral-100 disabled:text-disabled"
          >
            <Send size={16} aria-hidden />
          </button>
        </form>
        <p className="mt-2 text-xs text-secondary">Answers come only from this case and the bank’s policy files.</p>
      </div>
    </section>
  )
}

function Avatar() {
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700">
      <Bot size={16} aria-hidden />
    </span>
  )
}

function Message({ from, children }: { from: 'agent' | 'you'; children: React.ReactNode }) {
  if (from === 'you') {
    return (
      <li className="flex justify-end">
        <div className="max-w-[85%] rounded-card rounded-br-control bg-brand-50 px-3 py-2 text-primary">{children}</div>
      </li>
    )
  }
  return (
    <li className="flex gap-2.5">
      <Avatar />
      <div className="min-w-0 max-w-[90%] flex-1 text-body">{children}</div>
    </li>
  )
}
