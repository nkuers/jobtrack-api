import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import {
  activeStatuses,
  applicationStatuses,
  statusLabel,
  statusTone,
} from '@/features/applications/constants'
import type { ApplicationStatus } from '@/features/applications/api'
import { useAuth } from '@/features/auth/auth-context'
import { typeLabel as interviewTypeLabel } from '@/features/interviews/constants'

import { dashboardKey, getDashboard, type Dashboard } from './api'

const cardClass =
  'rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-slate-900'

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function DashboardSkeleton() {
  return (
    <div aria-label="正在加载总览" className="animate-pulse space-y-6">
      <div className="h-24 rounded-2xl bg-slate-200 dark:bg-slate-800" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div
            className="h-32 rounded-2xl bg-slate-200 dark:bg-slate-800"
            key={index}
          />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="h-96 rounded-2xl bg-slate-200 dark:bg-slate-800" />
        <div className="h-96 rounded-2xl bg-slate-200 dark:bg-slate-800" />
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  detail,
  to,
}: {
  label: string
  value: string | number
  detail: string
  to: string
}) {
  return (
    <Link
      className={`${cardClass} group block p-5 transition hover:-translate-y-0.5 hover:border-emerald-400 hover:shadow-md`}
      to={to}
    >
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 flex items-center justify-between text-xs text-slate-400">
        {detail}
        <span
          aria-hidden="true"
          className="transition group-hover:translate-x-1"
        >
          →
        </span>
      </p>
    </Link>
  )
}

function EmptyDashboard() {
  return (
    <section className={`${cardClass} mt-8 p-8 text-center sm:p-12`}>
      <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-emerald-400/15 text-xl text-emerald-600 dark:text-emerald-300">
        01
      </div>
      <h2 className="mt-4 text-xl font-semibold">从第一家目标公司开始</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm text-slate-500 dark:text-slate-400">
        添加公司和职位，再创建第一条投递。JobTrack
        会自动汇总状态、转化率、面试和下一步行动。
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link className="button-primary" to="/companies">
          添加公司
        </Link>
        <Link className="button-secondary" to="/jobs">
          查看职位
        </Link>
      </div>
    </section>
  )
}

function StatusDistribution({ dashboard }: { dashboard: Dashboard }) {
  const total = applicationStatuses.reduce(
    (sum, status) => sum + (dashboard.application_status_counts[status] ?? 0),
    0,
  )
  const maximum = Math.max(
    1,
    ...applicationStatuses.map(
      (status) => dashboard.application_status_counts[status] ?? 0,
    ),
  )

  return (
    <section className={`${cardClass} p-5 sm:p-6`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">投递状态分布</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            共 {total} 条投递，点击状态查看对应列表
          </p>
        </div>
        <span className="status-badge app-applied">
          近 7 天新增 {dashboard.applications_last_7_days}
        </span>
      </div>
      <div className="mt-6 space-y-4">
        {applicationStatuses.map((status) => {
          const count = dashboard.application_status_counts[status] ?? 0
          const percentage = Math.round((count / maximum) * 100)
          return (
            <Link
              aria-label={`${statusLabel[status]}：${count} 条投递`}
              className="group grid grid-cols-[4.75rem_1fr_2rem] items-center gap-3 text-sm"
              key={status}
              to={`/applications?status=${status}`}
            >
              <span
                className={`status-badge ${statusTone[status]} justify-center`}
              >
                {statusLabel[status]}
              </span>
              <span className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <span
                  className="block h-full rounded-full bg-emerald-400 transition-all group-hover:bg-emerald-300"
                  style={{ width: `${percentage}%` }}
                />
              </span>
              <span className="text-right font-semibold tabular-nums">
                {count}
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

function UpcomingInterviews({ dashboard }: { dashboard: Dashboard }) {
  return (
    <section className={`${cardClass} p-5 sm:p-6`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">未来 7 天面试</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            已按本地时间排序
          </p>
        </div>
        <Link className="text-link text-sm" to="/interviews">
          打开日历
        </Link>
      </div>
      {dashboard.upcoming_interviews.length ? (
        <ul className="mt-5 divide-y divide-slate-100 dark:divide-white/5">
          {dashboard.upcoming_interviews.map((interview) => {
            const job = interview.application_summary.job_summary
            return (
              <li key={interview.id}>
                <Link
                  className="group flex gap-4 py-4 first:pt-0 last:pb-0"
                  to={`/applications/${interview.application_id}`}
                >
                  <span className="mt-0.5 grid size-10 shrink-0 place-items-center rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-400/15 dark:text-violet-300">
                    ◇
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium group-hover:text-emerald-600 dark:group-hover:text-emerald-300">
                      {job.title}
                    </span>
                    <span className="mt-1 block truncate text-sm text-slate-500 dark:text-slate-400">
                      {job.company_summary.name} ·{' '}
                      {interviewTypeLabel[interview.interview_type]}
                    </span>
                    <span className="mt-2 block text-xs text-slate-400">
                      {formatDateTime(interview.scheduled_at)} ·{' '}
                      {interview.duration_minutes} 分钟
                    </span>
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-8 rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-500 dark:bg-white/[0.03] dark:text-slate-400">
          未来 7 天暂无面试，可以安心准备下一步。
        </p>
      )}
    </section>
  )
}

function ActionList({
  title,
  description,
  actions,
  overdue = false,
}: {
  title: string
  description: string
  actions: Dashboard['upcoming_actions']
  overdue?: boolean
}) {
  return (
    <section className={`${cardClass} p-5 sm:p-6`}>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        {description}
      </p>
      {actions.length ? (
        <ul className="mt-5 space-y-3">
          {actions.map((action) => (
            <li key={action.application_id}>
              <Link
                className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 p-4 transition hover:border-emerald-400 dark:border-white/10"
                to={`/applications/${action.application_id}`}
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {action.job_summary.title}
                  </span>
                  <span className="mt-1 block truncate text-xs text-slate-500 dark:text-slate-400">
                    {action.job_summary.company_summary.name} ·{' '}
                    {statusLabel[action.status]}
                  </span>
                </span>
                <span
                  className={`shrink-0 text-right text-xs font-medium ${overdue ? 'text-rose-600 dark:text-rose-300' : 'text-slate-500 dark:text-slate-400'}`}
                >
                  {formatDateTime(action.next_action_at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 text-sm text-slate-400">暂无事项</p>
      )}
    </section>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const dashboard = useQuery({ queryKey: dashboardKey, queryFn: getDashboard })

  if (dashboard.isPending) return <DashboardSkeleton />

  if (dashboard.isError) {
    return (
      <section className={`${cardClass} p-8 text-center`}>
        <h1 className="text-xl font-semibold">总览暂时无法加载</h1>
        <p className="mt-2 text-sm text-rose-600 dark:text-rose-300">
          {errorMessage(dashboard.error)}
        </p>
        <button
          className="button-secondary mt-5"
          onClick={() => void dashboard.refetch()}
        >
          重新加载
        </button>
      </section>
    )
  }

  const data = dashboard.data
  const totalApplications = applicationStatuses.reduce(
    (sum, status) => sum + (data.application_status_counts[status] ?? 0),
    0,
  )
  const activeApplications = activeStatuses.reduce(
    (sum, status: ApplicationStatus) =>
      sum + (data.application_status_counts[status] ?? 0),
    0,
  )
  const empty =
    data.company_count === 0 && data.job_count === 0 && totalApplications === 0

  return (
    <div>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="section-kicker">求职工作台</p>
            {user?.username === 'jobtrack_demo' && (
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-400/15 dark:text-amber-300">
                演示数据
              </span>
            )}
          </div>
          <h1 className="page-title">你好，{user?.username}</h1>
          <p className="page-description">
            今天从最重要的投递、面试和下一步行动开始。
          </p>
        </div>
        <div className="text-right">
          <button
            className="button-secondary"
            disabled={dashboard.isFetching}
            onClick={() => void dashboard.refetch()}
          >
            {dashboard.isFetching ? '正在刷新…' : '刷新数据'}
          </button>
          <p className="mt-2 text-xs text-slate-400">
            更新于 {formatDateTime(data.generated_at)}
          </p>
        </div>
      </header>

      {empty ? (
        <EmptyDashboard />
      ) : (
        <>
          <section className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              detail="管理目标公司"
              label="公司"
              to="/companies"
              value={data.company_count}
            />
            <MetricCard
              detail="查看全部职位"
              label="职位"
              to="/jobs"
              value={data.job_count}
            />
            <MetricCard
              detail={`全部投递 ${totalApplications}`}
              label="活跃投递"
              to="/applications"
              value={activeApplications}
            />
            <MetricCard
              detail="已申请投递中的 Offer 占比"
              label="Offer 转化率"
              to="/applications?status=offer"
              value={new Intl.NumberFormat('zh-CN', {
                style: 'percent',
                maximumFractionDigits: 1,
              }).format(data.offer_conversion_rate)}
            />
          </section>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <StatusDistribution dashboard={data} />
            <UpcomingInterviews dashboard={data} />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <ActionList
              actions={data.overdue_actions}
              description="这些行动已过计划时间，建议优先处理"
              overdue
              title="逾期行动"
            />
            <ActionList
              actions={data.upcoming_actions}
              description="未来 7 天需要跟进的投递"
              title="近期行动"
            />
          </div>
        </>
      )}
    </div>
  )
}
