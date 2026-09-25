import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { fieldClass } from '@/features/auth/auth-layout'

import type { Company, CompanyInput } from './api'

const optional = (max: number) => z.string().trim().max(max).optional()
const schema = z.object({
  name: z.string().trim().min(1, '请输入公司名称').max(120),
  website: z.union([
    z.literal(''),
    z.string().url('请输入完整网址，例如 https://example.com'),
  ]),
  industry: optional(100),
  location: optional(255),
  notes: optional(5000),
})
type Values = z.infer<typeof schema>

export function CompanyForm({
  company,
  busy,
  onSubmit,
  onCancel,
}: {
  company?: Company
  busy?: boolean
  onSubmit: (input: CompanyInput) => Promise<void>
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
      name: company?.name || '',
      website: company?.website || '',
      industry: company?.industry || '',
      location: company?.location || '',
      notes: company?.notes || '',
    },
  })
  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit({
        name: values.name,
        website: values.website || null,
        industry: values.industry || null,
        location: values.location || null,
        notes: values.notes || null,
      })
    } catch (error) {
      setError('root', { message: errorMessage(error) })
    }
  })
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {errors.root && (
        <div role="alert" className="error-box">
          {errors.root.message}
        </div>
      )}
      <label className="field-label">
        公司名称
        <input className={fieldClass} autoFocus {...register('name')} />
        {errors.name && (
          <span className="field-error">{errors.name.message}</span>
        )}
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="field-label">
          行业
          <input className={fieldClass} {...register('industry')} />
        </label>
        <label className="field-label">
          地点
          <input className={fieldClass} {...register('location')} />
        </label>
      </div>
      <label className="field-label">
        官网
        <input
          className={fieldClass}
          type="url"
          placeholder="https://example.com"
          {...register('website')}
        />
        {errors.website && (
          <span className="field-error">{errors.website.message}</span>
        )}
      </label>
      <label className="field-label">
        备注
        <textarea
          className={`${fieldClass} min-h-28 resize-y`}
          {...register('notes')}
        />
      </label>
      <div className="flex justify-end gap-3 pt-2">
        <button type="button" className="button-secondary" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在保存…' : '保存公司'}
        </button>
      </div>
    </form>
  )
}
