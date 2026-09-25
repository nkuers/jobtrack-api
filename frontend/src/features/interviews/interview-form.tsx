import { zodResolver } from '@hookform/resolvers/zod'
import { useForm, useWatch } from 'react-hook-form'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { fieldClass } from '@/features/auth/auth-layout'
import type { Application } from '@/features/applications/api'

import type { Interview, InterviewInput, InterviewUpdate } from './api'
import { statusLabel, toLocalInput, typeLabel } from './constants'

const schema = z
  .object({
    application_id: z.string().min(1, '请选择投递'),
    interview_type: z.enum([
      'phone_screen',
      'technical',
      'behavioral',
      'system_design',
      'hiring_manager',
      'onsite',
      'other',
    ]),
    status: z.enum(['scheduled', 'completed', 'cancelled']),
    scheduled_at: z.string().min(1, '请选择面试时间'),
    duration_minutes: z.coerce
      .number()
      .int()
      .min(15, '至少 15 分钟')
      .max(480, '最多 480 分钟'),
    location: z.string().max(255),
    meeting_url: z.union([z.literal(''), z.string().url('请输入完整会议链接')]),
    notes: z.string().max(10000),
    feedback: z.string().max(10000),
  })
  .refine((value) => !value.feedback.trim() || value.status === 'completed', {
    path: ['feedback'],
    message: '只有已完成的面试才能填写反馈',
  })
type Values = z.infer<typeof schema>
const optional = (value: string) => value.trim() || null
const defaultScheduledAt = toLocalInput(new Date(Date.now() + 86_400_000))

export function InterviewForm({
  interview,
  applications = [],
  initialDate,
  busy,
  onSubmit,
  onCancel,
}: {
  interview?: Interview
  applications?: Application[]
  initialDate?: Date
  busy?: boolean
  onSubmit: (input: InterviewInput | InterviewUpdate) => Promise<void>
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
      application_id: String(interview?.application_id || ''),
      interview_type: interview?.interview_type || 'technical',
      status: interview?.status || 'scheduled',
      scheduled_at: toLocalInput(
        interview?.scheduled_at || initialDate || defaultScheduledAt,
      ),
      duration_minutes: interview?.duration_minutes || 60,
      location: interview?.location || '',
      meeting_url: interview?.meeting_url || '',
      notes: interview?.notes || '',
      feedback: interview?.feedback || '',
    },
  })
  const status = useWatch({ control, name: 'status' })
  const submit = handleSubmit(async (value) => {
    try {
      const common = {
        interview_type: value.interview_type,
        scheduled_at: new Date(value.scheduled_at).toISOString(),
        duration_minutes: value.duration_minutes,
        location: optional(value.location),
        meeting_url: optional(value.meeting_url),
        notes: optional(value.notes),
      }
      await onSubmit(
        interview
          ? {
              ...common,
              status: value.status,
              feedback: optional(value.feedback),
            }
          : { ...common, application_id: Number(value.application_id) },
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
      {!interview && (
        <label className="field-label">
          投递
          <select className={fieldClass} {...register('application_id')}>
            <option value="">请选择投递</option>
            {applications.map((item) => (
              <option key={item.id} value={item.id}>
                {item.job_summary.company_summary.name} ·{' '}
                {item.job_summary.title}
              </option>
            ))}
          </select>
          {errors.application_id && (
            <span className="field-error">{errors.application_id.message}</span>
          )}
        </label>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          面试类型
          <select className={fieldClass} {...register('interview_type')}>
            {Object.entries(typeLabel).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {interview && (
          <label className="field-label">
            状态
            <select
              className={fieldClass}
              disabled={interview.status !== 'scheduled'}
              {...register('status')}
            >
              {interview.status === 'scheduled' ? (
                <>
                  <option value="scheduled">已安排</option>
                  <option value="completed">已完成</option>
                  <option value="cancelled">已取消</option>
                </>
              ) : (
                <option value={interview.status}>
                  {statusLabel[interview.status]}
                </option>
              )}
            </select>
          </label>
        )}
        <label className="field-label">
          开始时间
          <input
            className={fieldClass}
            type="datetime-local"
            {...register('scheduled_at')}
          />
          {errors.scheduled_at && (
            <span className="field-error">{errors.scheduled_at.message}</span>
          )}
        </label>
        <label className="field-label">
          时长（分钟）
          <input
            className={fieldClass}
            type="number"
            min="15"
            max="480"
            step="15"
            {...register('duration_minutes')}
          />
          {errors.duration_minutes && (
            <span className="field-error">
              {errors.duration_minutes.message}
            </span>
          )}
        </label>
        <label className="field-label">
          地点
          <input className={fieldClass} {...register('location')} />
        </label>
        <label className="field-label">
          会议链接
          <input
            className={fieldClass}
            type="url"
            {...register('meeting_url')}
          />
          {errors.meeting_url && (
            <span className="field-error">{errors.meeting_url.message}</span>
          )}
        </label>
      </div>
      <label className="field-label">
        准备笔记
        <textarea className={`${fieldClass} min-h-24`} {...register('notes')} />
      </label>
      {interview && (
        <label className="field-label">
          面试反馈
          <textarea
            className={`${fieldClass} min-h-24`}
            disabled={status !== 'completed'}
            {...register('feedback')}
          />
          {errors.feedback && (
            <span className="field-error">{errors.feedback.message}</span>
          )}
        </label>
      )}
      <div className="flex justify-end gap-3">
        <button type="button" className="button-secondary" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在保存…' : '保存面试'}
        </button>
      </div>
    </form>
  )
}
