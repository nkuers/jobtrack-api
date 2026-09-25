type ConfirmDialogProps = {
  open: boolean
  title: string
  description: string
  busy?: boolean
  confirmLabel?: string
  onCancel: () => void
  onConfirm: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  busy,
  confirmLabel = '确认',
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-950/70 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(event) =>
        event.target === event.currentTarget && onCancel()
      }
    >
      <section
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-description"
        className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-slate-900"
      >
        <h2 id="confirm-title" className="text-lg font-semibold">
          {title}
        </h2>
        <p
          id="confirm-description"
          className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300"
        >
          {description}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button
            className="button-secondary"
            onClick={onCancel}
            disabled={busy}
          >
            取消
          </button>
          <button
            className="button-primary"
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? '正在处理…' : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
