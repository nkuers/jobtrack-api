import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { Pagination } from '@/components/shared/pagination'
import { EmptyState, PageSkeleton } from '@/components/shared/states'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Modal } from '@/components/ui/modal'
import { useToast } from '@/components/ui/toast'
import { listCompanies } from '@/features/companies/api'
import { listJobs } from '@/features/jobs/api'

import { ApplicationForm } from './application-form'
import {
  changeApplicationStatus,
  createApplication,
  deleteApplication,
  getApplication,
  listApplicationHistory,
  listApplications,
  updateApplication,
  applicationKeys,
  type Application,
  type ApplicationInput,
  type ApplicationStatus,
  type ApplicationUpdate,
} from './api'
import {
  activeStatuses,
  allowedTransitions,
  applicationStatuses,
  formatLocalDateTime,
  statusLabel,
  statusTone,
  terminalStatuses,
} from './constants'

function StatusBadge({ status }: { status: ApplicationStatus }) {
  return (
    <span className={`status-badge ${statusTone[status]}`}>
      {statusLabel[status]}
    </span>
  )
}
function Priority({ value }: { value: number }) {
  return (
    <span aria-label={`优先级 ${value}`} className="text-amber-500">
      {'★'.repeat(6 - value)}
      <span className="text-slate-300 dark:text-slate-700">
        {'★'.repeat(value - 1)}
      </span>
    </span>
  )
}

function StatusActions({
  application,
  compact = false,
}: {
  application: Application
  compact?: boolean
}) {
  const client = useQueryClient()
  const { showToast } = useToast()
  const mutation = useMutation({
    mutationFn: (status: ApplicationStatus) =>
      changeApplicationStatus(application.id, status),
    onSuccess: async (_, status) => {
      await Promise.all([
        client.invalidateQueries({ queryKey: applicationKeys.all }),
        client.invalidateQueries({ queryKey: ['dashboard'] }),
      ])
      showToast(`状态已更新为“${statusLabel[status]}”。`)
    },
    onError: (error) => showToast(errorMessage(error), 'error'),
  })
  const targets = allowedTransitions[application.status]
  if (targets.length === 0)
    return <span className="text-xs text-slate-400">无后续状态</span>
  return (
    <div className={`flex flex-wrap gap-2 ${compact ? '' : 'mt-3'}`}>
      {targets.map((status) => (
        <button
          key={status}
          className={
            status === 'rejected' || status === 'withdrawn'
              ? 'button-secondary !min-h-8 !px-2.5 !py-1 text-xs'
              : 'button-primary !min-h-8 !px-2.5 !py-1 text-xs'
          }
          disabled={mutation.isPending}
          onClick={() => mutation.mutate(status)}
        >
          转为{statusLabel[status]}
        </button>
      ))}
    </div>
  )
}

export function ApplicationsPage() {
  const [params, setParams] = useSearchParams()
  const [createOpen, setCreateOpen] = useState(false)
  const filters = {
    status: (params.get('status') || undefined) as
      ApplicationStatus | undefined,
    company_id: params.get('company_id')
      ? Number(params.get('company_id'))
      : undefined,
    applied_from: params.get('applied_from') || undefined,
    applied_to: params.get('applied_to') || undefined,
    priority: params.get('priority')
      ? Number(params.get('priority'))
      : undefined,
    sort_by: (params.get('sort_by') || 'updated_at') as
      | 'created_at'
      | 'updated_at'
      | 'applied_at'
      | 'deadline'
      | 'next_action_at'
      | 'priority',
    sort_order: 'desc' as const,
    page: Number(params.get('page') || 1),
    page_size: 20,
  }
  const applications = useQuery({
    queryKey: applicationKeys.list(filters),
    queryFn: () => listApplications(filters),
  })
  const companies = useQuery({
    queryKey: ['companies', 'options'],
    queryFn: () => listCompanies({ page_size: 100 }),
  })
  const jobs = useQuery({
    queryKey: ['jobs', 'options'],
    queryFn: () => listJobs({ status: 'open', page_size: 100 }),
    enabled: createOpen,
  })
  const client = useQueryClient()
  const { showToast } = useToast()
  const create = useMutation({
    mutationFn: (input: ApplicationInput) => createApplication(input),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: applicationKeys.all })
      setCreateOpen(false)
      showToast('投递已创建。')
    },
  })
  const apply = (form: FormData) => {
    const next = new URLSearchParams()
    for (const key of [
      'status',
      'company_id',
      'applied_from',
      'applied_to',
      'priority',
      'sort_by',
    ]) {
      const value = String(form.get(key) || '')
      if (value) next.set(key, value)
    }
    setParams(next)
  }
  const pageTo = (page: number) => {
    const next = new URLSearchParams(params)
    next.set('page', String(page))
    setParams(next)
  }
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="section-kicker">求职管线</p>
          <h1 className="page-title">投递</h1>
          <p className="page-description">
            跟踪每一个机会的状态、优先级和下一步行动。
          </p>
        </div>
        <div className="flex gap-2">
          <Link className="button-secondary" to="/applications/board">
            看板视图
          </Link>
          <button
            className="button-primary"
            onClick={() => setCreateOpen(true)}
          >
            ＋ 新建投递
          </button>
        </div>
      </div>
      <form className="filter-bar" key={params.toString()} action={apply}>
        <select
          className="filter-input"
          name="status"
          defaultValue={filters.status || ''}
        >
          <option value="">全部状态</option>
          {applicationStatuses.map((status) => (
            <option key={status} value={status}>
              {statusLabel[status]}
            </option>
          ))}
        </select>
        <select
          className="filter-input"
          name="company_id"
          defaultValue={filters.company_id || ''}
        >
          <option value="">全部公司</option>
          {companies.data?.items.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
        <select
          className="filter-input"
          name="priority"
          defaultValue={filters.priority || ''}
        >
          <option value="">全部优先级</option>
          {[1, 2, 3, 4, 5].map((value) => (
            <option key={value} value={value}>
              优先级 {value}
            </option>
          ))}
        </select>
        <input
          className="filter-input"
          name="applied_from"
          type="date"
          defaultValue={filters.applied_from}
          aria-label="申请开始日期"
        />
        <input
          className="filter-input"
          name="applied_to"
          type="date"
          defaultValue={filters.applied_to}
          aria-label="申请结束日期"
        />
        <select
          className="filter-input"
          name="sort_by"
          defaultValue={filters.sort_by}
        >
          <option value="updated_at">最近更新</option>
          <option value="created_at">创建时间</option>
          <option value="applied_at">申请日期</option>
          <option value="deadline">截止日期</option>
          <option value="next_action_at">下一行动</option>
          <option value="priority">优先级</option>
        </select>
        <button className="button-secondary">筛选</button>
        <Link className="button-secondary" to="/applications">
          重置
        </Link>
      </form>
      {applications.isPending ? (
        <PageSkeleton />
      ) : applications.isError ? (
        <div className="error-box mt-6">{errorMessage(applications.error)}</div>
      ) : applications.data.items.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="还没有符合条件的投递"
            description="选择一个已创建的职位，建立第一条投递记录。"
          />
        </div>
      ) : (
        <>
          <div className="mt-6 space-y-3">
            {applications.data.items.map((item) => (
              <article
                key={item.id}
                className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-slate-900"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <Link to={`/applications/${item.id}`} className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold hover:text-emerald-600">
                        {item.job_summary.title}
                      </h2>
                      <StatusBadge status={item.status} />
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                      {item.job_summary.company_summary.name} ·{' '}
                      <Priority value={item.priority} />
                    </p>
                    <p className="mt-2 text-xs text-slate-400">
                      下一行动：{formatLocalDateTime(item.next_action_at)} ·
                      截止：{item.deadline || '—'}
                    </p>
                  </Link>
                  <StatusActions application={item} compact />
                </div>
              </article>
            ))}
          </div>
          <Pagination
            page={applications.data.page}
            pageSize={applications.data.page_size}
            total={applications.data.total}
            onPage={pageTo}
          />
        </>
      )}
      <Modal
        open={createOpen}
        title="新建投递"
        description="一个职位只能建立一条投递记录。"
        onClose={() => setCreateOpen(false)}
      >
        {jobs.isPending ? (
          <p>正在加载职位…</p>
        ) : jobs.isError ? (
          <div className="error-box">{errorMessage(jobs.error)}</div>
        ) : jobs.data.items.length === 0 ? (
          <div>
            <EmptyState
              title="没有可用职位"
              description="请先创建一个开放中的职位。"
            />
            <Link className="button-primary mt-4" to="/jobs">
              前往职位管理
            </Link>
          </div>
        ) : (
          <ApplicationForm
            jobs={jobs.data.items}
            busy={create.isPending}
            onCancel={() => setCreateOpen(false)}
            onSubmit={async (input) => {
              await create.mutateAsync(input as ApplicationInput)
            }}
          />
        )}
      </Modal>
    </div>
  )
}

export function ApplicationBoardPage() {
  const board = useQuery({
    queryKey: applicationKeys.list({ board: true }),
    queryFn: () =>
      listApplications({
        page_size: 100,
        sort_by: 'updated_at',
        sort_order: 'desc',
      }),
  })
  if (board.isPending) return <PageSkeleton />
  if (board.isError)
    return <div className="error-box">{errorMessage(board.error)}</div>
  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="section-kicker">流程总览</p>
          <h1 className="page-title">投递看板</h1>
          <p className="page-description">
            状态操作只提供后端状态机允许的目标。
          </p>
        </div>
        <Link className="button-secondary" to="/applications">
          列表视图
        </Link>
      </div>
      {board.data.total > 100 && (
        <div className="mt-5 rounded-xl bg-amber-100 p-3 text-sm text-amber-800">
          看板显示最近更新的 100 条投递，请使用列表筛选查看其余记录。
        </div>
      )}
      <div className="mt-6 flex gap-4 overflow-x-auto pb-4">
        {activeStatuses.map((status) => (
          <BoardColumn
            key={status}
            status={status}
            items={board.data.items.filter((item) => item.status === status)}
          />
        ))}
      </div>
      <details className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-slate-900">
        <summary className="cursor-pointer font-semibold">
          终态与归档（
          {
            board.data.items.filter((item) =>
              terminalStatuses.includes(item.status),
            ).length
          }
          ）
        </summary>
        <div className="mt-4 flex gap-4 overflow-x-auto pb-2">
          {terminalStatuses.map((status) => (
            <BoardColumn
              key={status}
              status={status}
              items={board.data.items.filter((item) => item.status === status)}
            />
          ))}
        </div>
      </details>
    </div>
  )
}
function BoardColumn({
  status,
  items,
}: {
  status: ApplicationStatus
  items: Application[]
}) {
  return (
    <section className="w-72 shrink-0 rounded-2xl bg-slate-100 p-3 dark:bg-slate-900">
      <header className="mb-3 flex items-center justify-between">
        <StatusBadge status={status} />
        <span className="text-xs text-slate-500">{items.length}</span>
      </header>
      <div className="space-y-3">
        {items.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-300 p-4 text-center text-xs text-slate-400 dark:border-slate-700">
            暂无投递
          </p>
        ) : (
          items.map((item) => (
            <article
              key={item.id}
              className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-slate-950"
            >
              <Link
                to={`/applications/${item.id}`}
                className="font-medium hover:text-emerald-500"
              >
                {item.job_summary.title}
              </Link>
              <p className="mt-1 text-xs text-slate-500">
                {item.job_summary.company_summary.name}
              </p>
              <StatusActions application={item} />
            </article>
          ))
        )}
      </div>
    </section>
  )
}

export function ApplicationDetailPage() {
  const id = Number(useParams().id)
  const application = useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => getApplication(id),
    enabled: Number.isInteger(id),
  })
  const history = useQuery({
    queryKey: applicationKeys.history(id),
    queryFn: () => listApplicationHistory(id),
    enabled: Number.isInteger(id),
  })
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const client = useQueryClient()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const update = useMutation({
    mutationFn: (input: ApplicationUpdate) => updateApplication(id, input),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: applicationKeys.all })
      setEditOpen(false)
      showToast('投递信息已更新。')
    },
  })
  const remove = useMutation({
    mutationFn: () => deleteApplication(id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: applicationKeys.all })
      showToast('投递已删除。')
      navigate('/applications')
    },
  })
  if (application.isPending) return <PageSkeleton />
  if (application.isError)
    return (
      <div>
        <Link className="text-link" to="/applications">
          ← 返回投递
        </Link>
        <div className="error-box mt-5">{errorMessage(application.error)}</div>
      </div>
    )
  const item = application.data
  return (
    <div>
      <Link className="text-link" to="/applications">
        ← 返回投递
      </Link>
      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="section-kicker">
              {item.job_summary.company_summary.name}
            </p>
            <StatusBadge status={item.status} />
          </div>
          <h1 className="page-title">{item.job_summary.title}</h1>
          <p className="page-description">
            优先级 {item.priority} · 创建于{' '}
            {new Date(item.created_at).toLocaleDateString('zh-CN')}
          </p>
          <StatusActions application={item} />
        </div>
        <div className="flex gap-2">
          <button
            className="button-secondary"
            onClick={() => setEditOpen(true)}
          >
            编辑
          </button>
          <button className="button-danger" onClick={() => setDeleteOpen(true)}>
            删除
          </button>
        </div>
      </div>
      <section className="detail-grid mt-8">
        <div>
          <dt>申请日期</dt>
          <dd>{item.applied_at || '—'}</dd>
        </div>
        <div>
          <dt>截止日期</dt>
          <dd>{item.deadline || '—'}</dd>
        </div>
        <div>
          <dt>下一行动</dt>
          <dd>{formatLocalDateTime(item.next_action_at)}</dd>
        </div>
        <div>
          <dt>关联职位</dt>
          <dd>
            <Link className="text-link" to={`/jobs/${item.job_id}`}>
              查看职位详情
            </Link>
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt>备注</dt>
          <dd className="whitespace-pre-wrap">{item.notes || '—'}</dd>
        </div>
      </section>
      <section className="mt-8">
        <h2 className="text-lg font-semibold">状态时间线</h2>
        {history.isPending ? (
          <p className="mt-4 text-sm text-slate-500">正在加载历史…</p>
        ) : history.isError ? (
          <div className="error-box mt-4">{errorMessage(history.error)}</div>
        ) : history.data.length === 0 ? (
          <p className="mt-4 rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-500 dark:border-slate-700">
            尚未发生状态迁移。
          </p>
        ) : (
          <ol className="mt-4 space-y-0">
            {history.data.map((entry) => (
              <li
                key={entry.id}
                className="relative border-l-2 border-emerald-300 pb-6 pl-5 last:pb-0"
              >
                <span className="absolute -left-[7px] top-1 size-3 rounded-full bg-emerald-400" />
                <p className="text-sm">
                  <strong>{statusLabel[entry.from_status]}</strong> →{' '}
                  <strong>{statusLabel[entry.to_status]}</strong>
                </p>
                <time className="mt-1 block text-xs text-slate-500">
                  {formatLocalDateTime(entry.changed_at)}
                </time>
              </li>
            ))}
          </ol>
        )}
      </section>
      <Modal
        open={editOpen}
        title="编辑投递"
        onClose={() => setEditOpen(false)}
      >
        <ApplicationForm
          application={item}
          busy={update.isPending}
          onCancel={() => setEditOpen(false)}
          onSubmit={async (input) => {
            await update.mutateAsync(input as ApplicationUpdate)
          }}
        />
      </Modal>
      <ConfirmDialog
        open={deleteOpen}
        title="删除这条投递？"
        description="如果投递下已有面试，服务端会拒绝删除并保留数据。"
        busy={remove.isPending}
        confirmLabel="确认删除"
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() =>
          void remove.mutateAsync().catch((error) => {
            showToast(errorMessage(error), 'error')
            setDeleteOpen(false)
          })
        }
      />
    </div>
  )
}
