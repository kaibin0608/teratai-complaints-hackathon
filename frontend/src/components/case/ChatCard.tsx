import { LoaderCircle, Send } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { ChatError, chatApi, type ChatTurn } from '@/api/chat'
import { Button } from '@/components/shared/Button'
import { Card } from '@/components/shared/Card'
import { controlClass } from '@/components/shared/FieldShell'
import { cx } from '@/lib/cx'
import type { CaseDetail } from '@/lib/types'

const SUGGESTIONS = ['Why this decision?', 'What does the evidence show?', 'Can I approve this myself?', 'Which policy applies?']

/**
 * Read-only case assistant (PLAN.md bonus X3): explains the decision, the evidence and the policy from the stored
 * facts. It can't change the case; the buttons below the page do that. Keyed by complaint, so history resets per case.
 */
export function ChatCard({ detail }: { detail: CaseDetail }) {
  const complaintId = detail.case.complaint_id
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    <Card title="Ask about this case" aside={<span className="text-xs text-secondary">Read-only assistant</span>}>
      <div className="flex flex-col gap-3">
        {turns.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <Button key={s} variant="secondary" className="h-8 text-xs" disabled={busy} onClick={() => void ask(s)}>
                {s}
              </Button>
            ))}
          </div>
        )}
        {turns.length > 0 && (
          <ol className="flex max-h-96 flex-col gap-2 overflow-y-auto" aria-live="polite">
            {turns.map((turn, index) => (
              <li
                key={index}
                className={cx(
                  'max-w-[90%] whitespace-pre-wrap rounded-control px-3 py-2 text-sm',
                  turn.role === 'user' ? 'self-end bg-brand-50 text-primary' : 'self-start border border-subtle bg-subtle text-body',
                )}
              >
                {turn.content}
              </li>
            ))}
            {busy && (
              <li role="status" className="flex items-center gap-2 self-start px-1 text-sm text-secondary">
                <LoaderCircle size={14} aria-hidden className="animate-spin" /> Thinking…
              </li>
            )}
          </ol>
        )}
        {error && <p className="text-sm text-error-700">{error}</p>}
        <form onSubmit={onSubmit} className="flex items-end gap-2">
          <label htmlFor={`chat-${complaintId}`} className="sr-only">
            Question about this case
          </label>
          <textarea
            id={`chat-${complaintId}`}
            rows={2}
            maxLength={1000}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void ask(draft)
              }
            }}
            placeholder="Ask why, what the evidence shows, or who can approve…"
            className={cx('min-w-0 flex-1 resize-none py-2 leading-relaxed', controlClass)}
            disabled={busy}
          />
          <Button type="submit" variant="primary" disabled={busy || !draft.trim()} aria-label="Ask">
            <Send size={16} aria-hidden />
          </Button>
        </form>
        <p className="text-xs text-secondary">Answers come only from this case's stored facts and the bank's policy files. It can't approve or send anything.</p>
      </div>
    </Card>
  )
}
