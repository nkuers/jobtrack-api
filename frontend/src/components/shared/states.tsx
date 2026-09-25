export function PageSkeleton() {
  return (
    <div className="grid min-h-screen place-items-center bg-slate-50 dark:bg-slate-950">
      <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
        <span className="size-2.5 animate-pulse rounded-full bg-emerald-400" />
        正在恢复会话…
      </div>
    </div>
  )
}

export function EmptyState({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <section className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-10 text-center dark:border-slate-700 dark:bg-slate-900/60">
      <div className="mx-auto grid size-11 place-items-center rounded-xl bg-emerald-400/15 text-xl text-emerald-500">
        +
      </div>
      <h2 className="mt-4 font-semibold">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>
    </section>
  )
}
