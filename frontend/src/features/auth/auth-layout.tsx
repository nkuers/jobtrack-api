import type { PropsWithChildren, ReactNode } from 'react'
import { Link } from 'react-router-dom'

export const fieldClass =
  'mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'

export function AuthLayout({
  eyebrow,
  title,
  description,
  footer,
  children,
}: PropsWithChildren<{
  eyebrow: string
  title: string
  description: string
  footer?: ReactNode
}>) {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 lg:grid lg:grid-cols-[1.05fr_.95fr]">
      <section className="relative hidden overflow-hidden border-r border-white/10 p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(52,211,153,.18),transparent_35%),radial-gradient(circle_at_80%_80%,rgba(14,165,233,.15),transparent_36%)]" />
        <Link to="/" className="relative flex items-center gap-3 font-semibold">
          <span className="grid size-10 place-items-center rounded-xl bg-emerald-400 font-black text-slate-950">
            JT
          </span>
          JobTrack
        </Link>
        <div className="relative max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-300">
            求职进度工作台
          </p>
          <p className="mt-5 text-4xl font-semibold leading-tight">
            把零散的申请、面试和下一步，整理成一条清晰的求职路径。
          </p>
          <p className="mt-5 leading-7 text-slate-400">
            从公司和职位，到投递状态与面试安排，所有行动都有迹可循。
          </p>
        </div>
        <p className="relative text-xs text-slate-500">
          FastAPI · React · OpenAPI typed
        </p>
      </section>
      <section className="flex min-h-screen items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <Link
            to="/"
            className="mb-10 flex items-center gap-3 font-semibold lg:hidden"
          >
            <span className="grid size-10 place-items-center rounded-xl bg-emerald-400 font-black text-slate-950">
              JT
            </span>
            JobTrack
          </Link>
          <p className="text-sm font-semibold text-emerald-300">{eyebrow}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {title}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-400">{description}</p>
          <div className="mt-8">{children}</div>
          {footer && (
            <div className="mt-7 text-center text-sm text-slate-400">
              {footer}
            </div>
          )}
        </div>
      </section>
    </main>
  )
}
