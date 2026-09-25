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

import {
  createJob,
  deleteJob,
  getJob,
  listJobs,
  updateJob,
  type JobInput,
} from './api'
import { JobForm } from './job-form'

const jobKeys = {
  all: ['jobs'] as const,
  list: (filters: object) => ['jobs', 'list', filters] as const,
  detail: (id: number) => ['jobs', 'detail', id] as const,
}
const statusLabel = { open: '开放', paused: '暂停', closed: '关闭' }
const modeLabel = { onsite: '现场', hybrid: '混合', remote: '远程' }
const employmentLabel = {
  full_time: '全职',
  part_time: '兼职',
  contract: '合同',
  internship: '实习',
  temporary: '临时',
}
const money = (min?: number | null, max?: number | null, currency = 'CNY') =>
  min == null && max == null
    ? '薪资未填写'
    : `${min == null ? '—' : min.toLocaleString()} – ${max == null ? '—' : max.toLocaleString()} ${currency}`

export function JobsPage() {
  const [params, setParams] = useSearchParams()
  const [createOpen, setCreateOpen] = useState(false)
  const filters = {
    keyword: params.get('keyword') || undefined,
    company_id: params.get('company_id')
      ? Number(params.get('company_id'))
      : undefined,
    status: (params.get('status') || undefined) as
      'open' | 'paused' | 'closed' | undefined,
    work_mode: (params.get('work_mode') || undefined) as
      'onsite' | 'hybrid' | 'remote' | undefined,
    sort_by: (params.get('sort_by') || 'created_at') as
      'created_at' | 'updated_at' | 'title' | 'salary_min' | 'salary_max',
    sort_order: (params.get('sort_order') || 'desc') as 'asc' | 'desc',
    page: Number(params.get('page') || 1),
    page_size: 20,
  }
  const jobs = useQuery({
    queryKey: jobKeys.list(filters),
    queryFn: () => listJobs(filters),
  })
  const companies = useQuery({
    queryKey: ['companies', 'options'],
    queryFn: () => listCompanies({ page_size: 100 }),
  })
  const client = useQueryClient()
  const { showToast } = useToast()
  const create = useMutation({
    mutationFn: createJob,
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: jobKeys.all })
      setCreateOpen(false)
      showToast('职位已创建。')
    },
  })
  const apply = (form: FormData) => {
    const next = new URLSearchParams()
    for (const key of [
      'keyword',
      'company_id',
      'status',
      'work_mode',
      'sort_by',
      'sort_order',
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
          <p className="section-kicker">机会管理</p>
          <h1 className="page-title">职位</h1>
          <p className="page-description">
            记录感兴趣的岗位，并按状态、公司和办公方式整理。
          </p>
        </div>
        <button className="button-primary" onClick={() => setCreateOpen(true)}>
          ＋ 新建职位
        </button>
      </div>
      <form
        className="filter-bar"
        key={params.toString()}
        action={(form) => apply(form)}
      >
        <input
          className="filter-input"
          name="keyword"
          placeholder="职位、地点或来源"
          defaultValue={filters.keyword}
        />
        <select
          className="filter-input"
          name="company_id"
          defaultValue={filters.company_id}
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
          name="status"
          defaultValue={filters.status || ''}
        >
          <option value="">全部状态</option>
          <option value="open">开放</option>
          <option value="paused">暂停</option>
          <option value="closed">关闭</option>
        </select>
        <select
          className="filter-input"
          name="work_mode"
          defaultValue={filters.work_mode || ''}
        >
          <option value="">全部方式</option>
          <option value="onsite">现场</option>
          <option value="hybrid">混合</option>
          <option value="remote">远程</option>
        </select>
        <select
          className="filter-input"
          name="sort_by"
          defaultValue={filters.sort_by}
        >
          <option value="created_at">创建时间</option>
          <option value="updated_at">更新时间</option>
          <option value="title">职位名称</option>
          <option value="salary_min">最低薪资</option>
        </select>
        <input type="hidden" name="sort_order" value={filters.sort_order} />
        <button className="button-secondary">筛选</button>
        <Link className="button-secondary" to="/jobs">
          重置
        </Link>
      </form>
      {jobs.isPending ? (
        <PageSkeleton />
      ) : jobs.isError ? (
        <div className="error-box mt-6">{errorMessage(jobs.error)}</div>
      ) : jobs.data.items.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="还没有职位"
            description="创建职位后就可以继续建立投递记录。"
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-3 md:hidden">
            {jobs.data.items.map((job) => (
              <Link className="list-card" key={job.id} to={`/jobs/${job.id}`}>
                <div>
                  <h2 className="font-semibold">{job.title}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {job.company_summary.name} · {modeLabel[job.work_mode]}
                  </p>
                  <p className="mt-2 text-xs text-slate-400">
                    {money(job.salary_min, job.salary_max, job.salary_currency)}
                  </p>
                </div>
                <span className={`status-badge status-${job.status}`}>
                  {statusLabel[job.status]}
                </span>
              </Link>
            ))}
          </div>
          <div className="data-table-wrap mt-6 hidden md:block">
            <table className="data-table">
              <thead>
                <tr>
                  <th>职位</th>
                  <th>公司</th>
                  <th>方式</th>
                  <th>薪资</th>
                  <th>状态</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.data.items.map((job) => (
                  <tr key={job.id}>
                    <td className="font-medium">{job.title}</td>
                    <td>{job.company_summary.name}</td>
                    <td>{modeLabel[job.work_mode]}</td>
                    <td>
                      {money(
                        job.salary_min,
                        job.salary_max,
                        job.salary_currency,
                      )}
                    </td>
                    <td>
                      <span className={`status-badge status-${job.status}`}>
                        {statusLabel[job.status]}
                      </span>
                    </td>
                    <td>
                      <Link className="text-link" to={`/jobs/${job.id}`}>
                        查看
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={jobs.data.page}
            pageSize={jobs.data.page_size}
            total={jobs.data.total}
            onPage={pageTo}
          />
        </>
      )}
      <Modal
        open={createOpen}
        title="新建职位"
        description={
          companies.data?.items.length === 0 ? '请先创建一家公司。' : undefined
        }
        onClose={() => setCreateOpen(false)}
      >
        {companies.isPending ? (
          <p>正在加载公司…</p>
        ) : companies.isError ? (
          <div className="error-box">{errorMessage(companies.error)}</div>
        ) : companies.data.items.length === 0 ? (
          <div>
            <EmptyState
              title="需要先创建公司"
              description="每个职位必须属于一家公司。"
            />
            <Link className="button-primary mt-4" to="/companies">
              前往创建公司
            </Link>
          </div>
        ) : (
          <JobForm
            companies={companies.data.items}
            busy={create.isPending}
            onCancel={() => setCreateOpen(false)}
            onSubmit={async (input) => {
              await create.mutateAsync(input)
            }}
          />
        )}
      </Modal>
    </div>
  )
}

export function JobDetailPage() {
  const id = Number(useParams().id)
  const job = useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: () => getJob(id),
    enabled: Number.isInteger(id),
  })
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const companies = useQuery({
    queryKey: ['companies', 'options'],
    queryFn: () => listCompanies({ page_size: 100 }),
    enabled: editOpen,
  })
  const client = useQueryClient()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const update = useMutation({
    mutationFn: (body: JobInput) => updateJob(id, body),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: jobKeys.all })
      setEditOpen(false)
      showToast('职位已更新。')
    },
  })
  const remove = useMutation({
    mutationFn: () => deleteJob(id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: jobKeys.all })
      showToast('职位已删除。')
      navigate('/jobs')
    },
  })
  if (job.isPending) return <PageSkeleton />
  if (job.isError)
    return (
      <div>
        <Link className="text-link" to="/jobs">
          ← 返回职位
        </Link>
        <div className="error-box mt-5">{errorMessage(job.error)}</div>
      </div>
    )
  const item = job.data
  return (
    <div>
      <Link className="text-link" to="/jobs">
        ← 返回职位
      </Link>
      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-kicker">{item.company_summary.name}</p>
          <h1 className="page-title">{item.title}</h1>
          <p className="page-description">
            {employmentLabel[item.employment_type]} ·{' '}
            {modeLabel[item.work_mode]} · {item.location || '地点未填写'}
          </p>
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
          <dt>状态</dt>
          <dd>
            <span className={`status-badge status-${item.status}`}>
              {statusLabel[item.status]}
            </span>
          </dd>
        </div>
        <div>
          <dt>薪资</dt>
          <dd>
            {money(item.salary_min, item.salary_max, item.salary_currency)}
          </dd>
        </div>
        <div>
          <dt>来源</dt>
          <dd>{item.source || '—'}</dd>
        </div>
        <div>
          <dt>职位链接</dt>
          <dd>
            {item.url ? (
              <a
                className="text-link"
                href={item.url}
                target="_blank"
                rel="noreferrer"
              >
                打开原始职位
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt>职位描述</dt>
          <dd className="whitespace-pre-wrap">{item.description || '—'}</dd>
        </div>
      </section>
      <Modal
        open={editOpen}
        title="编辑职位"
        onClose={() => setEditOpen(false)}
      >
        {companies.isPending ? (
          <p>正在加载公司…</p>
        ) : companies.isError ? (
          <div className="error-box">{errorMessage(companies.error)}</div>
        ) : (
          <JobForm
            job={item}
            companies={companies.data.items}
            busy={update.isPending}
            onCancel={() => setEditOpen(false)}
            onSubmit={async (input) => {
              await update.mutateAsync(input)
            }}
          />
        )}
      </Modal>
      <ConfirmDialog
        open={deleteOpen}
        title="删除这个职位？"
        description="如果职位下已有投递，服务端会拒绝删除并保留全部数据。"
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
