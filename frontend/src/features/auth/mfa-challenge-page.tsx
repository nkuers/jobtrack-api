import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'

import { AuthLayout, fieldClass } from './auth-layout'
import { useAuth } from './auth-context'

const schema = z.object({
  code: z.string().trim().min(6, '请输入至少 6 位验证码').max(32),
})
type FormValues = z.infer<typeof schema>

export function MfaChallengePage() {
  const { challenge, verifyChallenge } = useAuth()
  const navigate = useNavigate()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (!challenge) navigate('/login', { replace: true })
  }, [challenge, navigate])

  if (!challenge) return null

  const submit = handleSubmit(async ({ code }) => {
    setSubmitError(null)
    try {
      await verifyChallenge(code)
      navigate('/dashboard', { replace: true })
    } catch (error) {
      setSubmitError(errorMessage(error))
    }
  })

  return (
    <AuthLayout
      eyebrow="双重验证"
      title="确认是你本人"
      description={`请输入身份验证器中的验证码或一条恢复码。挑战将在约 ${Math.max(1, Math.ceil(challenge.expires_in / 60))} 分钟后失效。`}
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
          验证码或恢复码
          <input
            className={`${fieldClass} tracking-[0.2em]`}
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            {...register('code')}
          />
          {errors.code && (
            <span className="mt-1.5 block text-xs text-rose-300">
              {errors.code.message}
            </span>
          )}
        </label>
        <button
          className="button-primary w-full"
          type="submit"
          disabled={isSubmitting}
        >
          {isSubmitting ? '正在验证…' : '完成验证'}
        </button>
        <button
          className="w-full text-sm text-slate-400 hover:text-slate-200"
          type="button"
          onClick={() => navigate('/login', { replace: true })}
        >
          返回重新登录
        </button>
      </form>
    </AuthLayout>
  )
}
