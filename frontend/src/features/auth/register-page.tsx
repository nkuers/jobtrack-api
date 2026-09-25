import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { useToast } from '@/components/ui/toast'

import { register as registerUser } from './api'
import { AuthLayout, fieldClass } from './auth-layout'

const schema = z.object({
  username: z.string().trim().min(2, '用户名至少需要 2 个字符').max(64),
  email: z.union([z.literal(''), z.string().trim().email('请输入有效邮箱')]),
  password: z
    .string()
    .min(8, '密码至少需要 8 个字符')
    .max(72, '密码不能超过 72 个字符'),
})
type FormValues = z.infer<typeof schema>

export function RegisterPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '' },
  })

  const submit = handleSubmit(async (values) => {
    setSubmitError(null)
    try {
      await registerUser({
        username: values.username,
        password: values.password,
        email: values.email || null,
      })
      showToast('账号创建成功，请登录。')
      navigate('/login', { replace: true })
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  return (
    <AuthLayout
      eyebrow="开始记录"
      title="创建你的账号"
      description="只需用户名和密码；邮箱可选，用于后续账号恢复。"
      footer={
        <>
          已有账号？{' '}
          <Link className="font-medium text-emerald-300" to="/login">
            直接登录
          </Link>
        </>
      }
    >
      <form className="space-y-5" onSubmit={submit} noValidate>
        {submitError && (
          <div
            role="alert"
            className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200"
          >
            {submitError}
          </div>
        )}
        <label className="block text-sm font-medium">
          用户名
          <input
            className={fieldClass}
            autoComplete="username"
            autoFocus
            {...register('username')}
          />
          {errors.username && (
            <span className="mt-1.5 block text-xs text-rose-300">
              {errors.username.message}
            </span>
          )}
        </label>
        <label className="block text-sm font-medium">
          邮箱 <span className="font-normal text-slate-500">（可选）</span>
          <input
            className={fieldClass}
            type="email"
            autoComplete="email"
            {...register('email')}
          />
          {errors.email && (
            <span className="mt-1.5 block text-xs text-rose-300">
              {errors.email.message}
            </span>
          )}
        </label>
        <label className="block text-sm font-medium">
          密码
          <input
            className={fieldClass}
            type="password"
            autoComplete="new-password"
            {...register('password')}
          />
          {errors.password && (
            <span className="mt-1.5 block text-xs text-rose-300">
              {errors.password.message}
            </span>
          )}
        </label>
        <button
          className="button-primary w-full"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? '正在创建…' : '创建账号'}
        </button>
      </form>
    </AuthLayout>
  )
}
