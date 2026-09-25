import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { EmptyState, PageSkeleton } from '@/components/shared/states'
import { Pagination } from '@/components/shared/pagination'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Modal } from '@/components/ui/modal'
import { useToast } from '@/components/ui/toast'

import { CompanyForm } from './company-form'
import {
  createCompany,
  deleteCompany,
  getCompany,
  listCompanies,
  updateCompany,
  type CompanyInput,
} from './api'

const companyKeys = {
  all: ['companies'] as const,
  list: (filters: object) => ['companies', 'list', filters] as const,
  detail: (id: number) => ['companies', 'detail', id] as const,
}

export function CompaniesPage() {
  const [params, setParams] = useSearchParams()
  const [createOpen, setCreateOpen] = useState(false)
  const filters = {
    keyword: params.get('keyword') || undefined,
    industry: params.get('industry') || undefined,
    location: params.get('location') || undefined,
    page: Number(params.get('page') || 1),
    page_size: 20,
  }
  const companies = useQuery({
    queryKey: companyKeys.list(filters),
    queryFn: () => listCompanies(filters),
  })
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const create = useMutation({
    mutationFn: createCompany,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: companyKeys.all })
      setCreateOpen(false)
      showToast('公司已创建。')
    },
  })

  function applyFilters(form: FormData) {
    const next = new URLSearchParams()
    for (const key of ['keyword', 'industry', 'location']) {
      const value = String(form.get(key) || '').trim()
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
          <p className="section-kicker">关系管理</p>
          <h1 className="page-title">公司</h1>
          <p className="page-description">
            维护目标公司，职位和投递会从这里建立关联。
          </p>
        </div>
        <button className="button-primary" onClick={() => setCreateOpen(true)}>
          ＋ 新建公司
        </button>
      </div>
      <form
        className="filter-bar"
        key={params.toString()}
        action={(form) => applyFilters(form)}
      >
        <input
          className="filter-input"
          name="keyword"
          placeholder="搜索公司名称或备注"
          defaultValue={filters.keyword}
        />
        <input
          className="filter-input"
          name="industry"
          placeholder="行业"
          defaultValue={filters.industry}
        />
        <input
          className="filter-input"
          name="location"
          placeholder="地点"
          defaultValue={filters.location}
        />
        <button className="button-secondary">筛选</button>
        <Link className="button-secondary" to="/companies">
          重置
        </Link>
      </form>
      {companies.isPending ? (
        <PageSkeleton />
      ) : companies.isError ? (
        <div className="error-box mt-6" role="alert">
          {errorMessage(companies.error)}
        </div>
      ) : companies.data.items.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            title="还没有公司"
            description="先创建目标公司，之后就可以在公司下添加职位。"
          />
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-3 md:hidden">
            {companies.data.items.map((company) => (
              <Link
                className="list-card"
                key={company.id}
                to={`/companies/${company.id}`}
              >
                <div>
                  <h2 className="font-semibold">{company.name}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    {company.industry || '未填写行业'} ·{' '}
                    {company.location || '未填写地点'}
                  </p>
                </div>
                <span aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
          <div className="data-table-wrap mt-6 hidden md:block">
            <table className="data-table">
              <thead>
                <tr>
                  <th>公司</th>
                  <th>行业</th>
                  <th>地点</th>
                  <th>更新时间</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {companies.data.items.map((company) => (
                  <tr key={company.id}>
                    <td className="font-medium">{company.name}</td>
                    <td>{company.industry || '—'}</td>
                    <td>{company.location || '—'}</td>
                    <td>
                      {new Date(company.updated_at).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="text-right">
                      <Link
                        className="text-link"
                        to={`/companies/${company.id}`}
                      >
                        查看
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={companies.data.page}
            pageSize={companies.data.page_size}
            total={companies.data.total}
            onPage={pageTo}
          />
        </>
      )}
      <Modal
        open={createOpen}
        title="新建公司"
        description="职位创建前必须先选择一个公司。"
        onClose={() => setCreateOpen(false)}
      >
        <CompanyForm
          busy={create.isPending}
          onCancel={() => setCreateOpen(false)}
          onSubmit={async (input) => {
            await create.mutateAsync(input)
          }}
        />
      </Modal>
    </div>
  )
}

export function CompanyDetailPage() {
  const id = Number(useParams().id)
  const company = useQuery({
    queryKey: companyKeys.detail(id),
    queryFn: () => getCompany(id),
    enabled: Number.isInteger(id),
  })
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showToast } = useToast()
  const update = useMutation({
    mutationFn: (body: CompanyInput) => updateCompany(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: companyKeys.all })
      setEditOpen(false)
      showToast('公司信息已更新。')
    },
  })
  const remove = useMutation({
    mutationFn: () => deleteCompany(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: companyKeys.all })
      showToast('公司已删除。')
      navigate('/companies')
    },
  })
  if (company.isPending) return <PageSkeleton />
  if (company.isError)
    return (
      <div>
        <Link className="text-link" to="/companies">
          ← 返回公司
        </Link>
        <div className="error-box mt-5">{errorMessage(company.error)}</div>
      </div>
    )
  const item = company.data
  return (
    <div>
      <Link className="text-link" to="/companies">
        ← 返回公司
      </Link>
      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="section-kicker">公司详情</p>
          <h1 className="page-title">{item.name}</h1>
          <p className="page-description">
            {item.industry || '未填写行业'} · {item.location || '未填写地点'}
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
          <dt>官网</dt>
          <dd>
            {item.website ? (
              <a
                className="text-link"
                href={item.website}
                target="_blank"
                rel="noreferrer"
              >
                {item.website}
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div>
          <dt>创建时间</dt>
          <dd>{new Date(item.created_at).toLocaleString('zh-CN')}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt>备注</dt>
          <dd className="whitespace-pre-wrap">{item.notes || '—'}</dd>
        </div>
      </section>
      <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 dark:border-white/10 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold">关联职位</h2>
            <p className="mt-1 text-sm text-slate-500">
              查看该公司下的全部职位。
            </p>
          </div>
          <Link className="button-secondary" to={`/jobs?company_id=${item.id}`}>
            查看职位
          </Link>
        </div>
      </div>
      <Modal
        open={editOpen}
        title="编辑公司"
        onClose={() => setEditOpen(false)}
      >
        <CompanyForm
          company={item}
          busy={update.isPending}
          onCancel={() => setEditOpen(false)}
          onSubmit={async (input) => {
            await update.mutateAsync(input)
          }}
        />
      </Modal>
      <ConfirmDialog
        open={deleteOpen}
        title="删除这家公司？"
        description="删除后无法恢复；如果公司下仍有职位，服务端会拒绝操作并保留全部数据。"
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
