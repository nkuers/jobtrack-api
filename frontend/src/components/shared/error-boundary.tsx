import { Component, type ErrorInfo, type ReactNode } from 'react'

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('JobTrack render error', error, info.componentStack)
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="grid min-h-screen place-items-center bg-slate-950 p-6 text-slate-100">
          <section className="max-w-md text-center">
            <p className="text-sm font-semibold text-rose-300">页面加载失败</p>
            <h1 className="mt-2 text-3xl font-semibold">这里出了点问题</h1>
            <p className="mt-3 text-slate-400">
              刷新页面即可重新开始，数据不会因此改变。
            </p>
            <button
              className="button-primary mt-6"
              onClick={() => location.reload()}
            >
              刷新页面
            </button>
          </section>
        </main>
      )
    }
    return this.props.children
  }
}
