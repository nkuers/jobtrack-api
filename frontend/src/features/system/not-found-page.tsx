import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-center text-slate-100">
      <section>
        <p className="text-sm font-semibold text-emerald-300">404</p>
        <h1 className="mt-2 text-4xl font-semibold">页面不存在</h1>
        <p className="mt-3 text-slate-400">
          链接可能已失效，或者地址输入有误。
        </p>
        <Link className="button-primary mt-6 inline-flex" to="/dashboard">
          返回工作台
        </Link>
      </section>
    </main>
  )
}
