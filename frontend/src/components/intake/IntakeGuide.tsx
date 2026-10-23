import { Card } from '@/components/shared/Card'

const STEPS: readonly { title: string; text: string }[] = [
  { title: 'The agent reads it', text: 'It works out what the complaint is about, finds the matching transaction and applies the policy. This takes a few seconds.' },
  { title: 'It is routed', text: 'Safe cases are resolved on their own. Refunds over the limit and declines wait for an officer, and fraud goes to the fraud team.' },
  { title: 'It appears in its queue', text: 'It shows up in the right queue within seconds, with no refresh. Nothing is sent to the customer until a person approves it.' },
]

/** What happens after "Send", so someone rehearsing the live round knows where to look next. */
export function IntakeGuide() {
  return (
    <Card title="What happens next">
      <ol className="flex flex-col gap-4">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700 tabular-nums">{index + 1}</span>
            <div>
              <h3 className="text-sm font-semibold">{step.title}</h3>
              <p className="mt-0.5 text-sm leading-relaxed text-secondary">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  )
}
