import { CircleCheck, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router'
import { Banner } from '@/components/shared/Banner'
import type { NoticeState } from '@/hooks/useAdvance'

/** A one-off message handed over by the previous page (e.g. "Approved CMP-00244."), dismissible. */
export function NoticeBanner() {
  const location = useLocation()
  const navigate = useNavigate()
  const notice = (location.state as NoticeState | null)?.notice
  if (!notice) return null

  return (
    <div className="relative">
      <Banner tone="success" icon={CircleCheck} title={notice} />
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => navigate(`${location.pathname}${location.search}`, { replace: true, state: null })}
        className="absolute top-2 right-2 rounded-control p-1 text-success-800 hover:bg-success-100"
      >
        <X size={14} aria-hidden />
      </button>
    </div>
  )
}
