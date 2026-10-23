import { useState } from 'react'
import { IntakeForm } from '@/components/intake/IntakeForm'
import { IntakePaste } from '@/components/intake/IntakePaste'
import { SubmissionList } from '@/components/intake/SubmissionList'
import { Page } from '@/components/layout/Page'
import { Tabs } from '@/components/shared/Tabs'
import { useSubmissions } from '@/hooks/useSubmissions'

type Mode = 'form' | 'paste'

/**
 * Post a complaint the way the judges' laptop does (POST /complaints). For rehearsing the live round:
 * the case then appears in its queue on its own.
 */
export function Intake() {
  const [mode, setMode] = useState<Mode>('form')
  const { submissions, submit } = useSubmissions()
  const sending = submissions.some((s) => s.state === 'sending')

  return (
    <Page title="Intake">
      <div className="flex flex-col gap-section">
        <Tabs
          label="How to enter the complaint"
          value={mode}
          onChange={setMode}
          items={[
            { value: 'form', label: 'Form' },
            { value: 'paste', label: 'Paste CSV rows' },
          ]}
        />
        {mode === 'form' ? <IntakeForm disabled={sending} onSubmit={submit} /> : <IntakePaste disabled={sending} onSubmit={submit} />}
        <SubmissionList submissions={submissions} />
      </div>
    </Page>
  )
}
