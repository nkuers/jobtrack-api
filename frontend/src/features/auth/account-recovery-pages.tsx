import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router-dom'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'

import {
  confirmEmailVerification,
  confirmPasswordReset,
  requestEmailVerification,
  requestPasswordReset,
} from './account-recovery-api'
import { AuthLayout, fieldClass } from './auth-layout'
import { useAuth } from './auth-context'

const emailSchema = z.object({
  email: z
    .string()
    .trim()
    .email('请输入有效邮箱地址')
    .transform((email) => email.toLowerCase()),
})

const passwordSchema = z
  .object({
    newPassword: z
      .string()
      .min(12, '密码至少需要 12 个字符')
      .refine(
        (password) => new TextEncoder().encode(password).length <= 72,
        '密码不能超过 72 个 UTF-8 字节',
      ),
    confirmPassword: z.string(),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    message: '两次输入的密码不一致',
    path: ['confirmPassword'],
  })

type EmailValues = z.infer<typeof emailSchema>
type PasswordValues = z.infer<typeof passwordSchema>

const linkClass = 'font-medium text-emerald-300 hover:text-emerald-200'

function Alert({ children }: { children: string }) {
  return (
    <div
      role="alert"
      className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200"
    >
      {children}
    </div>
  )
}

function Success({ children }: { children: string }) {
  return (
    <div
      role="status"
      className="rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm leading-6 text-emerald-100"
    >
      {children}
    </div>
  )
}

function BackToLogin() {
  return (
    <Link className={linkClass} to="/login">
      返回登录
    </Link>
  )
}

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EmailValues>({ resolver: zodResolver(emailSchema) })

  const submit = handleSubmit(async ({ email }) => {
    setSubmitError(null)
    try {
      await requestPasswordReset(email)
      setSent(true)
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  return (
    <AuthLayout
      eyebrow="账号恢复"
      title="重置密码"
      description="输入账号邮箱。无论账号是否存在，页面都会显示相同结果，避免泄露注册状态。"
      footer={<BackToLogin />}
    >
      {sent ? (
        <Success>
          如果该邮箱符合条件，重置邮件会很快发送，请检查收件箱和垃圾邮件。
        </Success>
      ) : (
        <form className="space-y-5" onSubmit={submit} noValidate>
          {submitError && <Alert>{submitError}</Alert>}
          <label className="block text-sm font-medium">
            邮箱
            <input
              className={fieldClass}
              type="email"
              autoComplete="email"
              autoFocus
              {...register('email')}
            />
            {errors.email && (
              <span className="mt-1.5 block text-xs text-rose-300">
                {errors.email.message}
              </span>
            )}
          </label>
          <button
            className="button-primary w-full"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? '正在发送…' : '发送重置邮件'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

export function VerifyEmailPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [token] = useState(() => searchParams.get('token')?.trim() ?? '')
  const [sent, setSent] = useState(false)
  const [verified, setVerified] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [isConfirming, setIsConfirming] = useState(false)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<EmailValues>({ resolver: zodResolver(emailSchema) })

  useEffect(() => {
    if (searchParams.has('token')) setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  const request = handleSubmit(async ({ email }) => {
    setSubmitError(null)
    try {
      await requestEmailVerification(email)
      setSent(true)
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  const confirm = async () => {
    setSubmitError(null)
    setIsConfirming(true)
    try {
      await confirmEmailVerification(token)
      setVerified(true)
    } catch (error) {
      setSubmitError(errorMessage(error))
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <AuthLayout
      eyebrow="邮箱安全"
      title="验证邮箱"
      description={
        token
          ? '确认此链接以完成邮箱验证。验证令牌已从地址栏移除。'
          : '输入账号邮箱，我们会发送新的验证链接。'
      }
      footer={<BackToLogin />}
    >
      {verified ? (
        <Success>邮箱验证成功，现在可以返回登录。</Success>
      ) : token ? (
        <div className="space-y-5">
          {submitError && <Alert>{submitError}</Alert>}
          <button
            className="button-primary w-full"
            type="button"
            disabled={isConfirming}
            onClick={() => void confirm()}
          >
            {isConfirming ? '正在验证…' : '验证邮箱'}
          </button>
        </div>
      ) : sent ? (
        <Success>
          如果该邮箱符合条件，验证邮件会很快发送，请检查收件箱和垃圾邮件。
        </Success>
      ) : (
        <form className="space-y-5" onSubmit={request} noValidate>
          {submitError && <Alert>{submitError}</Alert>}
          <label className="block text-sm font-medium">
            邮箱
            <input
              className={fieldClass}
              type="email"
              autoComplete="email"
              autoFocus
              {...register('email')}
            />
            {errors.email && (
              <span className="mt-1.5 block text-xs text-rose-300">
                {errors.email.message}
              </span>
            )}
          </label>
          <button
            className="button-primary w-full"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? '正在发送…' : '发送验证邮件'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}

export function ResetPasswordPage() {
  const { clearLocalSession } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [token] = useState(() => searchParams.get('token')?.trim() ?? '')
  const [changed, setChanged] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PasswordValues>({ resolver: zodResolver(passwordSchema) })

  useEffect(() => {
    if (searchParams.has('token')) setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  const submit = handleSubmit(async ({ newPassword }) => {
    setSubmitError(null)
    try {
      await confirmPasswordReset(token, newPassword)
      clearLocalSession()
      setChanged(true)
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  return (
    <AuthLayout
      eyebrow="账号恢复"
      title="设置新密码"
      description="密码至少 12 个字符。成功后所有设备会话都会失效，需要重新登录。"
      footer={<BackToLogin />}
    >
      {changed ? (
        <Success>密码已更新，所有设备会话已失效。请使用新密码登录。</Success>
      ) : !token ? (
        <div className="space-y-5">
          <Alert>重置链接缺少令牌，请重新申请密码重置邮件。</Alert>
          <Link
            className="button-primary block w-full text-center"
            to="/forgot-password"
          >
            重新申请
          </Link>
        </div>
      ) : (
        <form className="space-y-5" onSubmit={submit} noValidate>
          {submitError && <Alert>{submitError}</Alert>}
          <label className="block text-sm font-medium">
            新密码
            <input
              className={fieldClass}
              type="password"
              autoComplete="new-password"
              autoFocus
              {...register('newPassword')}
            />
            {errors.newPassword && (
              <span className="mt-1.5 block text-xs text-rose-300">
                {errors.newPassword.message}
              </span>
            )}
          </label>
          <label className="block text-sm font-medium">
            确认新密码
            <input
              className={fieldClass}
              type="password"
              autoComplete="new-password"
              {...register('confirmPassword')}
            />
            {errors.confirmPassword && (
              <span className="mt-1.5 block text-xs text-rose-300">
                {errors.confirmPassword.message}
              </span>
            )}
          </label>
          <button
            className="button-primary w-full"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? '正在更新…' : '更新密码'}
          </button>
        </form>
      )}
    </AuthLayout>
  )
}
