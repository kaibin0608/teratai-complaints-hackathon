import { X } from 'lucide-react'
import { useEffect, useRef, type ReactNode } from 'react'

interface DialogProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
}

/**
 * Modal on the browser's native <dialog>: focus is trapped, Esc closes, and the page behind is inert.
 * Floating layers are the one place a shadow is allowed (Colour System §1).
 */
export function Dialog({ open, title, onClose, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(event) => event.target === event.currentTarget && onClose()}
      aria-labelledby="dialog-title"
      className="m-auto w-full max-w-lg rounded-card border border-default bg-card p-0 text-body shadow-overlay backdrop:bg-(--overlay-scrim)"
    >
      {open && (
        <div className="flex flex-col">
          <header className="flex items-center justify-between gap-3 border-b border-default px-card py-3">
            <h2 id="dialog-title" className="text-base font-semibold">
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded-control p-1 text-secondary hover:bg-subtle hover:text-primary"
            >
              <X size={16} aria-hidden />
            </button>
          </header>
          {children}
        </div>
      )}
    </dialog>
  )
}
