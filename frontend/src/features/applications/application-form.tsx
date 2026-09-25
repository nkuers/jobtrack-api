import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { fieldClass } from '@/features/auth/auth-layout'
import type { Job } from '@/features/jobs/api'

import type { Application, ApplicationInput, ApplicationUpdate } from './api'

const schema = z
  .object({
    job_id: z.string().min(1, '请选择职位'),
    status: z.enum([
      'saved',
      'applied',
      'screening',
      'interview',
      'offer',
      'rejected',
      'withdrawn',
      'archived',
    ]),
    priority: z.string(),
    applied_at: z.string(),
    deadline: z.string(),
    next_action_at: z.string(),
    notes: z.string().max(10000),
  })
  .refine(
    (value) =>
      !value.applied_at ||
      !value.deadline ||
      value.deadline >= value.applied_at,
    { path: ['deadline'], message: '截止日期不能早于申请日期' },
  )
  .refine((value) => value.status !== 'saved' || !value.applied_at, {
    path: ['applied_at'],
    message: '收藏状态不能填写申请日期',
  })
type Values = z.infer<typeof schema>
const localInput = (value?: string | null) =>
  value ? new Date(value).toISOString().slice(0, 16) : ''

export function ApplicationForm({
  application,
  jobs = [],
  busy,
  onSubmit,
  onCancel,
}: {
  application?: Application
  jobs?: Job[]
  busy?: boolean
  onSubmit: (input: ApplicationInput | ApplicationUpdate) => Promise<void>
  onCancel: () => void
}) {
  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      job_id: String(application?.job_id || ''),
      status: application?.status || 'saved',
      priority: String(application?.priority || 3),
      applied_at: application?.applied_at || '',
      deadline: application?.deadline || '',
      next_action_at: localInput(application?.next_action_at),
      notes: application?.notes || '',
    },
  })
  const status = useWatch({ control, name: 'status' })
  const submit = handleSubmit(async (value) => {
    try {
      const common = {
        priority: Number(value.priority),
        applied_at: value.applied_at || null,
        deadline: value.deadline || null,
        next_action_at: value.next_action_at
          ? new Date(value.next_action_at).toISOString()
          : null,
        notes: value.notes.trim() || null,
      }
      await onSubmit(
        application
          ? common
          : { ...common, job_id: Number(value.job_id), status: value.status },
      )
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
      {!application && (
        <>
          <label className="field-label">
            职位
            <select className={fieldClass} {...register('job_id')} required>
              <option value="">请选择职位</option>
              {jobs.map((job) => (
                <option key={job.id} value={job.id}>
                  {job.company_summary.name} · {job.title}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            初始状态
            <select className={fieldClass} {...register('status')}>
              <option value="saved">已收藏</option>
              <option value="applied">已申请</option>
            </select>
          </label>
        </>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          优先级
          <select className={fieldClass} {...register('priority')}>
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value} {value === 1 ? '· 最高' : value === 5 ? '· 最低' : ''}
              </option>
            ))}
          </select>
          {errors.job_id && (
            <span className="field-error">{errors.job_id.message}</span>
          )}
        </label>
        <label className="field-label">
          申请日期
          <input
            className={fieldClass}
            type="date"
            disabled={!application && status === 'saved'}
            {...register('applied_at')}
          />
          {errors.applied_at && (
            <span className="field-error">{errors.applied_at.message}</span>
          )}
        </label>
        <label className="field-label">
          截止日期
          <input className={fieldClass} type="date" {...register('deadline')} />
          {errors.deadline && (
            <span className="field-error">{errors.deadline.message}</span>
          )}
        </label>
        <label className="field-label">
          下一行动时间
          <input
            className={fieldClass}
            type="datetime-local"
            {...register('next_action_at')}
          />
        </label>
      </div>
      <label className="field-label">
        备注
        <textarea className={`${fieldClass} min-h-32`} {...register('notes')} />
      </label>
      <div className="flex justify-end gap-3">
        <button type="button" className="button-secondary" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在保存…' : '保存投递'}
        </button>
      </div>
    </form>
  )
}
