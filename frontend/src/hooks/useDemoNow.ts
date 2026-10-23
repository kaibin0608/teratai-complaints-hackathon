import { useSyncExternalStore } from 'react'
import { demoNow } from '@/lib/clock'
import type { IsoTime } from '@/lib/types'

/*
 * One shared 1-second ticker for every clock and SLA timer on screen.
 * It runs only while at least one component is subscribed.
 */
const listeners = new Set<() => void>()
let snapshot: IsoTime = demoNow()
let timer: ReturnType<typeof setInterval> | undefined

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  if (timer === undefined) {
    snapshot = demoNow()
    timer = setInterval(() => {
      snapshot = demoNow()
      listeners.forEach((notify) => notify())
    }, 1000)
  }
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      clearInterval(timer)
      timer = undefined
    }
  }
}

/** Current demo-clock time (naive MYT), re-rendering once per second. */
export function useDemoNow(): IsoTime {
  return useSyncExternalStore(subscribe, () => snapshot)
}
