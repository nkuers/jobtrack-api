import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import QRCode from 'qrcode'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { z } from 'zod'

import { errorMessage } from '@/api/errors'
import { EmptyState } from '@/components/shared/states'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Modal } from '@/components/ui/modal'
import { useToast } from '@/components/ui/toast'
import { fieldClass } from '@/features/auth/auth-layout'
import { useAuth } from '@/features/auth/auth-context'

import {
  confirmTotp,
  disableMfa,
  enrollTotp,
  getMfaStatus,
  listDeviceSessions,
  regenerateRecoveryCodes,
  revokeAllDeviceSessions,
  revokeDeviceSession,
  type DeviceSession,
  type MfaEnrollment,
} from './api'

const securityKeys = {
  mfa: ['settings', 'mfa'] as const,
  sessions: ['settings', 'sessions'] as const,
}

const passwordSchema = z.object({
  password: z
    .string()
    .min(1, '请输入当前密码')
    .max(72, '密码不能超过 72 个字符'),
})
const verificationSchema = z.object({
  password: z
    .string()
    .min(1, '请输入当前密码')
    .max(72, '密码不能超过 72 个字符'),
  code: z.string().trim().min(1, '请输入验证码').max(64, '验证码格式不正确'),
})
const totpSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^\d{6}$/, '请输入 6 位动态验证码'),
})

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function InlineQueryError({
  error,
  retry,
}: {
  error: unknown
  retry: () => void
}) {
  return (
    <div className="error-box" role="alert">
      <p>{errorMessage(error)}</p>
      <button className="button-secondary mt-3" type="button" onClick={retry}>
        重试
      </button>
    </div>
  )
}

function PasswordForm({
  busy,
  submitLabel,
  onCancel,
  onSubmit,
}: {
  busy: boolean
  submitLabel: string
  onCancel: () => void
  onSubmit: (password: string) => Promise<void>
}) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
  })
  const submit = handleSubmit(async ({ password }) => {
    try {
      await onSubmit(password)
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
      <label className="field-label">
        当前密码
        <input
          className={fieldClass}
          type="password"
          autoComplete="current-password"
          autoFocus
          {...register('password')}
        />
        {errors.password && (
          <span className="field-error">{errors.password.message}</span>
        )}
      </label>
      <div className="flex justify-end gap-3 pt-2">
        <button className="button-secondary" type="button" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在验证…' : submitLabel}
        </button>
      </div>
    </form>
  )
}

function VerificationForm({
  busy,
  submitLabel,
  allowRecoveryCode = false,
  onCancel,
  onSubmit,
}: {
  busy: boolean
  submitLabel: string
  allowRecoveryCode?: boolean
  onCancel: () => void
  onSubmit: (input: { password: string; code: string }) => Promise<void>
}) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<z.infer<typeof verificationSchema>>({
    resolver: zodResolver(verificationSchema),
  })
  const submit = handleSubmit(async (values) => {
    try {
      await onSubmit({ ...values, code: values.code.trim() })
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
      <label className="field-label">
        当前密码
        <input
          className={fieldClass}
          type="password"
          autoComplete="current-password"
          autoFocus
          {...register('password')}
        />
        {errors.password && (
          <span className="field-error">{errors.password.message}</span>
        )}
      </label>
      <label className="field-label">
        {allowRecoveryCode ? '动态验证码或恢复码' : '动态验证码'}
        <input
          className={fieldClass}
          inputMode="numeric"
          autoComplete="one-time-code"
          {...register('code')}
        />
        {errors.code && (
          <span className="field-error">{errors.code.message}</span>
        )}
      </label>
      <div className="flex justify-end gap-3 pt-2">
        <button className="button-secondary" type="button" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在处理…' : submitLabel}
        </button>
      </div>
    </form>
  )
}

function EnrollmentStep({
  enrollment,
  qrSvg,
  busy,
  onCancel,
  onConfirm,
}: {
  enrollment: MfaEnrollment
  qrSvg: string
  busy: boolean
  onCancel: () => void
  onConfirm: (code: string) => Promise<void>
}) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<z.infer<typeof totpSchema>>({
    resolver: zodResolver(totpSchema),
  })
  const submit = handleSubmit(async ({ code }) => {
    try {
      await onConfirm(code)
    } catch (error) {
      setError('root', { message: errorMessage(error) })
    }
  })
  return (
    <form className="space-y-5" onSubmit={submit} noValidate>
      {errors.root && (
        <div className="error-box" role="alert">
          {errors.root.message}
        </div>
      )}
      <div className="grid gap-5 sm:grid-cols-[12rem_1fr] sm:items-center">
        <div
          className="mx-auto size-48 overflow-hidden rounded-xl bg-white p-2 [&>svg]:size-full"
          aria-label="MFA 设置二维码"
          dangerouslySetInnerHTML={{ __html: qrSvg }}
        />
        <div className="min-w-0 space-y-3 text-sm">
          <p className="text-slate-600 dark:text-slate-300">
            使用身份验证器扫描二维码，或手动输入下面的密钥。二维码完全在此浏览器中生成。
          </p>
          <div>
            <span className="text-xs text-slate-500">手动密钥</span>
            <code className="mt-1 block break-all rounded-lg bg-slate-100 p-2 font-mono text-xs dark:bg-slate-950">
              {enrollment.secret}
            </code>
          </div>
          <p className="text-xs text-amber-700 dark:text-amber-300">
            此设置于 {formatDateTime(enrollment.expires_at)} 过期。
          </p>
        </div>
      </div>
      <label className="field-label">
        6 位动态验证码
        <input
          className={fieldClass}
          inputMode="numeric"
          autoComplete="one-time-code"
          autoFocus
          {...register('code')}
        />
        {errors.code && (
          <span className="field-error">{errors.code.message}</span>
        )}
      </label>
      <div className="flex justify-end gap-3">
        <button className="button-secondary" type="button" onClick={onCancel}>
          取消
        </button>
        <button className="button-primary" disabled={busy}>
          {busy ? '正在启用…' : '确认并启用'}
        </button>
      </div>
    </form>
  )
}

function RecoveryCodesView({
  codes,
  loggingOutAfterClose,
  onClose,
}: {
  codes: string[]
  loggingOutAfterClose: boolean
  onClose: () => void
}) {
  const { showToast } = useToast()
  const content = codes.join('\n')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      showToast('恢复码已复制。')
    } catch {
      showToast('无法访问剪贴板，请手动保存恢复码。', 'error')
    }
  }
  const download = () => {
    const url = URL.createObjectURL(
      new Blob([`${content}\n`], { type: 'text/plain;charset=utf-8' }),
    )
    const link = document.createElement('a')
    link.href = url
    link.download = 'jobtrack-recovery-codes.txt'
    link.click()
    URL.revokeObjectURL(url)
  }
  return (
    <div>
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
        这些恢复码只显示一次，关闭后无法再次查看。请现在复制或下载并安全保存。
        {loggingOutAfterClose && ' 关闭后你需要重新登录。'}
      </div>
      <ul className="mt-4 grid gap-2 rounded-xl bg-slate-100 p-4 font-mono text-sm sm:grid-cols-2 dark:bg-slate-950">
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <div className="mt-5 flex flex-wrap justify-end gap-3">
        <button
          className="button-secondary"
          type="button"
          onClick={() => void copy()}
        >
          复制恢复码
        </button>
        <button className="button-secondary" type="button" onClick={download}>
          下载恢复码
        </button>
        <button className="button-primary" type="button" onClick={onClose}>
          我已安全保存
        </button>
      </div>
    </div>
  )
}

export function SecurityPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { clearLocalSession } = useAuth()
  const { showToast } = useToast()
  const [mfaDialog, setMfaDialog] = useState<
    'enroll-password' | 'regenerate' | 'disable' | null
  >(null)
  const [enrollment, setEnrollment] = useState<MfaEnrollment | null>(null)
  const [qrSvg, setQrSvg] = useState('')
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null)
  const [logoutAfterRecoveryClose, setLogoutAfterRecoveryClose] =
    useState(false)
  const [sessionToRevoke, setSessionToRevoke] = useState<DeviceSession | null>(
    null,
  )
  const [revokeAllOpen, setRevokeAllOpen] = useState(false)
  const [sessionActionError, setSessionActionError] = useState<string | null>(
    null,
  )

  const mfa = useQuery({
    queryKey: securityKeys.mfa,
    queryFn: getMfaStatus,
  })
  const sessions = useQuery({
    queryKey: securityKeys.sessions,
    queryFn: listDeviceSessions,
  })

  const leaveAuthenticatedArea = () => {
    queryClient.clear()
    clearLocalSession()
    navigate('/login', { replace: true })
  }

  useEffect(() => {
    if (!logoutAfterRecoveryClose) return
    return () => {
      queryClient.clear()
      clearLocalSession()
    }
  }, [clearLocalSession, logoutAfterRecoveryClose, queryClient])

  const enroll = useMutation({
    mutationFn: enrollTotp,
    onSuccess: async (data) => {
      const svg = await QRCode.toString(data.provisioning_uri, {
        type: 'svg',
        margin: 1,
        width: 256,
      })
      setEnrollment(data)
      setQrSvg(svg)
      setMfaDialog(null)
    },
  })
  const confirm = useMutation({
    mutationFn: confirmTotp,
    onSuccess: async (data) => {
      setEnrollment(null)
      setQrSvg('')
      setRecoveryCodes(data.recovery_codes)
      setLogoutAfterRecoveryClose(false)
      await queryClient.invalidateQueries({ queryKey: securityKeys.mfa })
      showToast('多因素认证已启用。')
    },
  })
  const regenerate = useMutation({
    mutationFn: regenerateRecoveryCodes,
    onSuccess: (data) => {
      setMfaDialog(null)
      setRecoveryCodes(data.recovery_codes)
      setLogoutAfterRecoveryClose(true)
    },
  })
  const disable = useMutation({
    mutationFn: disableMfa,
    onSuccess: () => {
      setMfaDialog(null)
      showToast('多因素认证已关闭，请重新登录。')
      leaveAuthenticatedArea()
    },
  })
  const revokeOne = useMutation({
    mutationFn: revokeDeviceSession,
    onSuccess: async () => {
      setSessionToRevoke(null)
      setSessionActionError(null)
      await queryClient.invalidateQueries({
        queryKey: securityKeys.sessions,
      })
      showToast('设备会话已撤销。')
    },
    onError: (error) => setSessionActionError(errorMessage(error)),
  })
  const revokeAll = useMutation({
    mutationFn: revokeAllDeviceSessions,
    onSuccess: () => {
      setRevokeAllOpen(false)
      showToast('全部设备会话已撤销，请重新登录。')
      leaveAuthenticatedArea()
    },
    onError: (error) => {
      setRevokeAllOpen(false)
      setSessionActionError(errorMessage(error))
    },
  })

  const closeEnrollment = () => {
    setEnrollment(null)
    setQrSvg('')
    confirm.reset()
  }
  const closeRecoveryCodes = () => {
    const shouldLogout = logoutAfterRecoveryClose
    setRecoveryCodes(null)
    setLogoutAfterRecoveryClose(false)
    if (shouldLogout) leaveAuthenticatedArea()
  }

  return (
    <div>
      <div>
        <p className="section-kicker">账号保护</p>
        <h1 className="page-title">安全设置</h1>
        <p className="page-description">
          管理多因素认证和仍可刷新登录状态的设备会话。
        </p>
      </div>

      <section className="mt-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-white/10 dark:bg-slate-900">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">多因素认证</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              使用身份验证器生成的一次性动态验证码保护账号。
            </p>
          </div>
          {mfa.data && (
            <span
              className={`status-badge ${
                mfa.data.enabled ? 'status-open' : 'status-closed'
              }`}
            >
              {mfa.data.enabled ? '已启用' : '未启用'}
            </span>
          )}
        </div>
        <div className="mt-5">
          {mfa.isPending ? (
            <p className="text-sm text-slate-500">正在加载 MFA 状态…</p>
          ) : mfa.isError ? (
            <InlineQueryError
              error={mfa.error}
              retry={() => void mfa.refetch()}
            />
          ) : mfa.data.enabled ? (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-slate-50 p-4 dark:bg-slate-950/60">
              <div>
                <p className="font-medium">
                  恢复码剩余 {mfa.data.recovery_codes_remaining} 个
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  重置恢复码或关闭 MFA 后，所有设备都需要重新登录。
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  className="button-secondary"
                  onClick={() => setMfaDialog('regenerate')}
                >
                  重置恢复码
                </button>
                <button
                  className="button-danger"
                  onClick={() => setMfaDialog('disable')}
                >
                  关闭 MFA
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-slate-50 p-4 dark:bg-slate-950/60">
              <p className="text-sm text-slate-600 dark:text-slate-300">
                启用后，登录需要密码和身份验证器中的动态验证码。
              </p>
              <button
                className="button-primary"
                onClick={() => setMfaDialog('enroll-password')}
              >
                启用 MFA
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6 dark:border-white/10 dark:bg-slate-900">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">设备会话</h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              后端不提供当前设备标识，因此列表不会猜测或标注“当前设备”。
            </p>
          </div>
          <button
            className="button-danger"
            disabled={!sessions.data?.length}
            onClick={() => {
              setSessionActionError(null)
              setRevokeAllOpen(true)
            }}
          >
            撤销全部会话
          </button>
        </div>
        {sessionActionError && (
          <div className="error-box mt-4" role="alert">
            {sessionActionError}
          </div>
        )}
        <div className="mt-5">
          {sessions.isPending ? (
            <p className="text-sm text-slate-500">正在加载设备会话…</p>
          ) : sessions.isError ? (
            <InlineQueryError
              error={sessions.error}
              retry={() => void sessions.refetch()}
            />
          ) : sessions.data.length === 0 ? (
            <EmptyState
              title="没有活跃设备会话"
              description="新的登录会话会显示在这里。"
            />
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-white/10">
              {sessions.data.map((session) => (
                <li
                  key={session.id}
                  className="flex flex-col gap-4 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <h3 className="truncate font-medium">
                      {session.device_name}
                    </h3>
                    <dl className="mt-2 grid gap-x-5 gap-y-1 text-xs text-slate-500 sm:grid-cols-3">
                      <div>
                        <dt className="inline">创建：</dt>
                        <dd className="inline">
                          {formatDateTime(session.created_at)}
                        </dd>
                      </div>
                      <div>
                        <dt className="inline">最后使用：</dt>
                        <dd className="inline">
                          {formatDateTime(session.last_used_at)}
                        </dd>
                      </div>
                      <div>
                        <dt className="inline">过期：</dt>
                        <dd className="inline">
                          {formatDateTime(session.expires_at)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                  <button
                    className="button-secondary shrink-0"
                    onClick={() => {
                      setSessionActionError(null)
                      setSessionToRevoke(session)
                    }}
                  >
                    撤销
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <Modal
        open={mfaDialog === 'enroll-password'}
        title="启用多因素认证"
        description="先验证当前密码，再绑定身份验证器。"
        onClose={() => setMfaDialog(null)}
      >
        <PasswordForm
          busy={enroll.isPending}
          submitLabel="继续设置"
          onCancel={() => setMfaDialog(null)}
          onSubmit={(password) =>
            enroll.mutateAsync(password).then(() => undefined)
          }
        />
      </Modal>
      <Modal
        open={Boolean(enrollment)}
        title="绑定身份验证器"
        description="密钥仅用于此次绑定，不会发送给二维码服务。"
        onClose={closeEnrollment}
      >
        {enrollment && qrSvg && (
          <EnrollmentStep
            enrollment={enrollment}
            qrSvg={qrSvg}
            busy={confirm.isPending}
            onCancel={closeEnrollment}
            onConfirm={(code) =>
              confirm.mutateAsync(code).then(() => undefined)
            }
          />
        )}
      </Modal>
      <Modal
        open={mfaDialog === 'regenerate'}
        title="重置恢复码"
        description="旧恢复码将立即失效，全部设备会话也会被撤销。"
        onClose={() => setMfaDialog(null)}
      >
        <VerificationForm
          busy={regenerate.isPending}
          submitLabel="生成新恢复码"
          onCancel={() => setMfaDialog(null)}
          onSubmit={(input) =>
            regenerate.mutateAsync(input).then(() => undefined)
          }
        />
      </Modal>
      <Modal
        open={mfaDialog === 'disable'}
        title="关闭多因素认证"
        description="成功后全部设备会话会被撤销，并立即返回登录页。"
        onClose={() => setMfaDialog(null)}
      >
        <VerificationForm
          busy={disable.isPending}
          submitLabel="确认关闭"
          allowRecoveryCode
          onCancel={() => setMfaDialog(null)}
          onSubmit={(input) => disable.mutateAsync(input).then(() => undefined)}
        />
      </Modal>
      <Modal
        open={Boolean(recoveryCodes)}
        title="保存恢复码"
        description="每个恢复码只能使用一次。"
        onClose={closeRecoveryCodes}
      >
        {recoveryCodes && (
          <RecoveryCodesView
            codes={recoveryCodes}
            loggingOutAfterClose={logoutAfterRecoveryClose}
            onClose={closeRecoveryCodes}
          />
        )}
      </Modal>
      <ConfirmDialog
        open={Boolean(sessionToRevoke)}
        title="撤销这个设备会话？"
        description={`将撤销“${sessionToRevoke?.device_name || ''}”的 refresh session。它可能正好是当前会话；后端未提供可提前判断的信息。`}
        busy={revokeOne.isPending}
        confirmLabel="确认撤销"
        onCancel={() => setSessionToRevoke(null)}
        onConfirm={() =>
          sessionToRevoke && revokeOne.mutate(sessionToRevoke.id)
        }
      />
      <ConfirmDialog
        open={revokeAllOpen}
        title="撤销全部设备会话？"
        description="所有设备的 refresh session 都会失效，当前页面也会立即退出。"
        busy={revokeAll.isPending}
        confirmLabel="撤销全部并退出"
        onCancel={() => setRevokeAllOpen(false)}
        onConfirm={() => revokeAll.mutate()}
      />
    </div>
  )
}
