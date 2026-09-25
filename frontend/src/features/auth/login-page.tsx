import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'

import { AuthLayout, fieldClass } from './auth-layout'
import { useAuth } from './auth-context'

const schema = z.object({
  username: z.string().trim().min(1, '请输入用户名'),
  password: z.string().min(1, '请输入密码').max(72, '密码不能超过 72 个字符'),
})
type FormValues = z.infer<typeof schema>

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const submit = handleSubmit(async (values) => {
    setSubmitError(null)
    try {
      const result = await login(values.username, values.password)
      if (result === 'mfa') {
        navigate('/mfa/challenge')
        return
      }
      const target = (location.state as { from?: { pathname?: string } } | null)
        ?.from?.pathname
      navigate(target || '/dashboard', { replace: true })
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  return (
    <AuthLayout
      eyebrow="欢迎回来"
      title="登录 JobTrack"
      description="继续管理你的求职进度。会话令牌不会被写入本地永久存储。"
      footer={
        <>
          还没有账号？{' '}
          <Link
            className="font-medium text-emerald-300 hover:text-emerald-200"
            to="/register"
          >
            创建账号
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
          密码
          <input
            className={fieldClass}
            type="password"
            autoComplete="current-password"
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
          {isSubmitting ? '正在登录…' : '登录'}
        </button>
      </form>
    </AuthLayout>
  )
}
