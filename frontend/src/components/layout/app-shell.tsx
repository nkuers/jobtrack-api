import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { useToast } from '@/components/ui/toast'
import { useAuth } from '@/features/auth/auth-context'

const navigation = [
  { to: '/dashboard', label: '总览', icon: '◫' },
  { to: '/applications', label: '投递', icon: '◎' },
  { to: '/interviews', label: '面试', icon: '◇' },
  { to: '/jobs', label: '职位', icon: '▤' },
  { to: '/companies', label: '公司', icon: '▦' },
  { to: '/settings/security', label: '设置', icon: '⚙' },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [logoutOpen, setLogoutOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [dark, setDark] = useState(
    () => localStorage.getItem('jobtrack.theme') !== 'light',
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('jobtrack.theme', dark ? 'dark' : 'light')
  }, [dark])

  const confirmLogout = async () => {
    setLoggingOut(true)
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(errorMessage(error), 'error')
    } finally {
      setLoggingOut(false)
      setLogoutOpen(false)
    }
  }

  const sidebar = (
    <>
      <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-5 dark:border-white/10">
        <span className="grid size-9 place-items-center rounded-xl bg-emerald-400 font-black text-slate-950">
          JT
        </span>
        <span className="font-semibold">JobTrack</span>
      </div>
      <nav className="flex-1 space-y-1 p-3" aria-label="主导航">
        {navigation.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${isActive ? 'bg-emerald-400/15 text-emerald-700 dark:text-emerald-300' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/5'}`
            }
          >
            <span className="w-5 text-center" aria-hidden="true">
              {item.icon}
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-200 p-4 dark:border-white/10">
        <p className="truncate text-sm font-medium">{user?.username}</p>
        <p className="truncate text-xs text-slate-500">
          {user?.email || user?.role}
        </p>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-60 flex-col border-r border-slate-200 bg-white lg:flex dark:border-white/10 dark:bg-slate-900/80">
        {sidebar}
      </aside>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/60 lg:hidden"
          onMouseDown={() => setMobileOpen(false)}
        >
          <aside
            className="flex h-full w-72 flex-col bg-white shadow-2xl dark:bg-slate-900"
            onMouseDown={(event) => event.stopPropagation()}
          >
            {sidebar}
          </aside>
        </div>
      )}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur sm:px-6 dark:border-white/10 dark:bg-slate-950/80">
          <div className="flex items-center gap-3">
            <button
              className="grid size-9 place-items-center rounded-lg border border-slate-200 lg:hidden dark:border-slate-700"
              aria-label="打开导航"
              onClick={() => setMobileOpen(true)}
            >
              ☰
            </button>
            <div>
              <p className="text-xs text-slate-500">工作空间</p>
              <p className="text-sm font-semibold">
                {navigation.find((item) =>
                  location.pathname.startsWith(item.to),
                )?.label || 'JobTrack'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="button-secondary !px-3"
              aria-label="切换主题"
              onClick={() => setDark((value) => !value)}
            >
              {dark ? '☀' : '☾'}
            </button>
            <button
              className="button-secondary"
              onClick={() => setLogoutOpen(true)}
            >
              退出
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
      <ConfirmDialog
        open={logoutOpen}
        title="退出当前会话？"
        description="当前设备的 refresh token 将被服务端撤销，需要重新登录后才能继续。"
        busy={loggingOut}
        confirmLabel="确认退出"
        onCancel={() => setLogoutOpen(false)}
        onConfirm={() => void confirmLogout()}
      />
    </div>
  )
}
