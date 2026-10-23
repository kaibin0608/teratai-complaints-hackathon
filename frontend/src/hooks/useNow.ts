import { useSyncExternalStore } from 'react'
import { now } from '@/lib/clock'
import type { IsoTime } from '@/lib/types'

/*
 * One shared 1-second ticker for every clock and SLA timer on screen.
 * It runs only while at least one component is subscribed.
 */
const listeners = new Set<() => void>()
let snapshot: IsoTime = now()
let timer: ReturnType<typeof setInterval> | undefined

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  if (timer === undefined) {
    snapshot = now()
    timer = setInterval(() => {
      snapshot = now()
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

/** Current time (naive MYT), re-rendering once per second. */
export function useNow(): IsoTime {
  return useSyncExternalStore(subscribe, () => snapshot)
}
