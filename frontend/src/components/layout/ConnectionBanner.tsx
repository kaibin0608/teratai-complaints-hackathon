import { WifiOff } from 'lucide-react'
import { Banner } from '@/components/shared/Banner'
import { useConnection } from '@/hooks/useConnection'
import { msToMyt } from '@/lib/clock'

/** Shown while the backend does not answer: what is on screen may be out of date. Clears itself when polling gets through. */
export function ConnectionBanner() {
  const { reachable, lastOkAt } = useConnection()
  if (reachable) return null
  const since = lastOkAt ? msToMyt(lastOkAt).slice(11, 16) : null
  return (
    <div className="px-page pt-4">
      <Banner tone="error" icon={WifiOff} title="Can’t reach the server">
        {since ? `What you see is from ${since} and may be out of date. ` : ''}Retrying on its own; actions will fail until it is back.
      </Banner>
    </div>
  )
}
