import { Page } from '@/components/layout/Page'
import { CaseQueue } from '@/components/queue/CaseQueue'
import { MANAGER_TABS } from '@/components/queue/queueTabs'

/** Every queue (manager): the core view the judges watch during the human gate. */
export function Cases() {
  return (
    <Page title="Cases">
      <CaseQueue tabs={MANAGER_TABS} />
    </Page>
  )
}
