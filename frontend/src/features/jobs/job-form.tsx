import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { fieldClass } from '@/features/auth/auth-layout'
import type { Company } from '@/features/companies/api'

import type { Job, JobInput } from './api'

const schema = z
  .object({
    company_id: z.string().min(1, '请选择公司'),
    title: z.string().trim().min(1, '请输入职位名称').max(200),
    employment_type: z.enum([
      'full_time',
      'part_time',
      'contract',
      'internship',
      'temporary',
    ]),
    work_mode: z.enum(['onsite', 'hybrid', 'remote']),
    location: z.string().trim().max(255),
    source: z.string().trim().max(100),
    url: z.union([z.literal(''), z.string().url('请输入完整职位链接')]),
    salary_min: z.string(),
    salary_max: z.string(),
    salary_currency: z.string().regex(/^[A-Za-z]{3}$/, '请输入 3 位货币代码'),
    description: z.string().max(20000),
    status: z.enum(['open', 'paused', 'closed']),
  })
  .refine(
    (value) =>
      !value.salary_min ||
      !value.salary_max ||
      Number(value.salary_min) <= Number(value.salary_max),
    { path: ['salary_max'], message: '最高薪资不能低于最低薪资' },
  )
type Values = z.infer<typeof schema>
const emptyToNull = (value: string) => value.trim() || null
const salary = (value: string) => (value === '' ? null : Number(value))

export function JobForm({
  job,
  companies,
  busy,
  onSubmit,
  onCancel,
}: {
  job?: Job
  companies: Company[]
  busy?: boolean
  onSubmit: (input: JobInput) => Promise<void>
  onCancel: () => void
}) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_id: String(job?.company_id || ''),
      title: job?.title || '',
      employment_type: job?.employment_type || 'full_time',
      work_mode: job?.work_mode || 'onsite',
      location: job?.location || '',
      source: job?.source || '',
      url: job?.url || '',
      salary_min: job?.salary_min == null ? '' : String(job.salary_min),
      salary_max: job?.salary_max == null ? '' : String(job.salary_max),
      salary_currency: job?.salary_currency || 'CNY',
      description: job?.description || '',
      status: job?.status || 'open',
    },
  })
  const submit = handleSubmit(async (value) => {
    try {
      await onSubmit({
        company_id: Number(value.company_id),
        title: value.title,
        employment_type: value.employment_type,
        work_mode: value.work_mode,
        location: emptyToNull(value.location),
        source: emptyToNull(value.source),
        url: emptyToNull(value.url),
        salary_min: salary(value.salary_min),
        salary_max: salary(value.salary_max),
        salary_currency: value.salary_currency.toUpperCase(),
        description: emptyToNull(value.description),
        status: value.status,
      })
    } catch (error) {
      setError('root', { message: errorMessage(error) })
    }
  })
  return (
    <form className="space-y-4" onSubmit={submit} noValidate>
      {errors.root && (
        <div className="error-box" role="alert">
          {errors.root.message}
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          公司
          <select className={fieldClass} {...register('company_id')}>
            <option value="">请选择公司</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
          {errors.company_id && (
            <span className="field-error">{errors.company_id.message}</span>
          )}
        </label>
        <label className="field-label">
          职位名称
          <input className={fieldClass} autoFocus {...register('title')} />
          {errors.title && (
            <span className="field-error">{errors.title.message}</span>
          )}
        </label>
        <label className="field-label">
          雇佣类型
          <select className={fieldClass} {...register('employment_type')}>
            <option value="full_time">全职</option>
            <option value="part_time">兼职</option>
            <option value="contract">合同</option>
            <option value="internship">实习</option>
            <option value="temporary">临时</option>
          </select>
        </label>
        <label className="field-label">
          办公方式
          <select className={fieldClass} {...register('work_mode')}>
            <option value="onsite">现场</option>
            <option value="hybrid">混合</option>
            <option value="remote">远程</option>
          </select>
        </label>
        <label className="field-label">
          地点
          <input className={fieldClass} {...register('location')} />
        </label>
        <label className="field-label">
          来源
          <input className={fieldClass} {...register('source')} />
        </label>
        <label className="field-label">
          最低薪资
          <input
            className={fieldClass}
            type="number"
            min="0"
            {...register('salary_min')}
          />
        </label>
        <label className="field-label">
          最高薪资
          <input
            className={fieldClass}
            type="number"
            min="0"
            {...register('salary_max')}
          />
          {errors.salary_max && (
            <span className="field-error">{errors.salary_max.message}</span>
          )}
        </label>
        <label className="field-label">
          货币
          <input
            className={fieldClass}
            maxLength={3}
            {...register('salary_currency')}
          />
          {errors.salary_currency && (
            <span className="field-error">
              {errors.salary_currency.message}
            </span>
          )}
        </label>
        <label className="field-label">
          状态
          <select className={fieldClass} {...register('status')}>
            <option value="open">开放</option>
            <option value="paused">暂停</option>
            <option value="closed">关闭</option>
          </select>
        </label>
      </div>
      <label className="field-label">
        职位链接
        <input className={fieldClass} type="url" {...register('url')} />
        {errors.url && (
          <span className="field-error">{errors.url.message}</span>
        )}
      </label>
      <label className="field-label">
        职位描述
        <textarea
          className={`${fieldClass} min-h-28`}
          {...register('description')}
        />
      </label>
      <div className="flex justify-end gap-3">
        <button type="button" className="button-secondary" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在保存…' : '保存职位'}
        </button>
      </div>
    </form>
  )
}
