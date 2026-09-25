import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { MemoryRouter } from 'react-router-dom'
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  expect,
  test,
} from 'vitest'

import { AppRoutes } from './App'
import { ToastProvider } from './components/ui/toast'
import { AuthProvider } from './features/auth/auth-context'
import { resetSessionForTests } from './features/auth/session'

const user = {
  id: 1,
  username: 'joker',
  role: 'user',
  email: 'joker@example.com',
  email_verified_at: null,
}

const emptyDashboard = {
  company_count: 0,
  job_count: 0,
  application_status_counts: {
    saved: 0,
    applied: 0,
    screening: 0,
    interview: 0,
    offer: 0,
    rejected: 0,
    withdrawn: 0,
    archived: 0,
  },
  applications_last_7_days: 0,
  offer_conversion_rate: 0,
  upcoming_interviews: [],
  overdue_actions: [],
  upcoming_actions: [],
  generated_at: '2026-09-24T04:00:00Z',
}

const server = setupServer(
  http.get('*/api/v1/dashboard', () => HttpResponse.json(emptyDashboard)),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => resetSessionForTests())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderApp(path = '/login') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[path]}>
            <AppRoutes />
          </MemoryRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

test('logs in and enters the protected application shell', async () => {
  server.use(
    http.post('*/login/', async ({ request }) => {
      expect(request.headers.get('x-device-name')).toContain('JobTrack Web')
      expect(request.headers.get('content-type')).toBe(
        'application/x-www-form-urlencoded',
      )
      expect(await request.text()).toContain('username=joker')
      return HttpResponse.json({
        access_token: 'access-1',
        refresh_token: 'refresh-1',
        token_type: 'bearer',
      })
    }),
    http.get('*/auth/me', ({ request }) => {
      expect(request.headers.get('authorization')).toBe('Bearer access-1')
      return HttpResponse.json(user)
    }),
  )

  renderApp()
  const actor = userEvent.setup()
  await actor.type(await screen.findByLabelText('用户名'), 'joker')
  await actor.type(screen.getByLabelText('密码'), 'correct-password')
  await actor.click(screen.getByRole('button', { name: '登录' }))

  expect(
    await screen.findByRole('heading', { name: '你好，joker' }),
  ).toBeInTheDocument()
  expect(sessionStorage.getItem('jobtrack.refresh-token')).toBe('refresh-1')
  expect(localStorage.getItem('access_token')).toBeNull()
})

test('continues an MFA login challenge without putting the challenge in the URL', async () => {
  server.use(
    http.post('*/login/', () =>
      HttpResponse.json({
        mfa_required: true,
        challenge_token: 'challenge-token-that-is-long-enough',
        expires_in: 300,
      }),
    ),
    http.post('*/auth/mfa/challenge/verify', async ({ request }) => {
      const body = (await request.json()) as {
        challenge_token: string
        code: string
      }
      expect(body).toEqual({
        challenge_token: 'challenge-token-that-is-long-enough',
        code: '123456',
      })
      return HttpResponse.json({
        access_token: 'access-mfa',
        refresh_token: 'refresh-mfa',
        token_type: 'bearer',
      })
    }),
    http.get('*/auth/me', () => HttpResponse.json(user)),
  )

  renderApp()
  const actor = userEvent.setup()
  await actor.type(await screen.findByLabelText('用户名'), 'joker')
  await actor.type(screen.getByLabelText('密码'), 'correct-password')
  await actor.click(screen.getByRole('button', { name: '登录' }))
  await actor.type(await screen.findByLabelText('验证码或恢复码'), '123456')
  expect(location.search).not.toContain('challenge')
  await actor.click(screen.getByRole('button', { name: '完成验证' }))
  expect(
    await screen.findByRole('heading', { name: '你好，joker' }),
  ).toBeInTheDocument()
})

test('redirects an anonymous visitor away from protected routes', async () => {
  renderApp('/dashboard')
  expect(
    await screen.findByRole('heading', { name: '登录 JobTrack' }),
  ).toBeInTheDocument()
})

test('restores the current user by rotating a stored refresh token', async () => {
  sessionStorage.setItem('jobtrack.refresh-token', 'stored-refresh')
  server.use(
    http.post('*/auth/refresh', async ({ request }) => {
      expect(await request.json()).toEqual({ refresh_token: 'stored-refresh' })
      return HttpResponse.json({
        access_token: 'restored-access',
        refresh_token: 'rotated-refresh',
        token_type: 'bearer',
      })
    }),
    http.get('*/auth/me', ({ request }) => {
      expect(request.headers.get('authorization')).toBe(
        'Bearer restored-access',
      )
      return HttpResponse.json(user)
    }),
  )

  renderApp('/dashboard')
  expect(
    await screen.findByRole('heading', { name: '你好，joker' }),
  ).toBeInTheDocument()
  expect(sessionStorage.getItem('jobtrack.refresh-token')).toBe(
    'rotated-refresh',
  )
})

test('clears an invalid refresh token and returns to login without retrying', async () => {
  let attempts = 0
  sessionStorage.setItem('jobtrack.refresh-token', 'invalid-refresh')
  server.use(
    http.post('*/auth/refresh', () => {
      attempts += 1
      return HttpResponse.json(
        { detail: 'Invalid refresh token' },
        { status: 401 },
      )
    }),
  )

  renderApp('/dashboard')
  expect(
    await screen.findByRole('heading', { name: '登录 JobTrack' }),
  ).toBeInTheDocument()
  expect(attempts).toBe(1)
  expect(sessionStorage.getItem('jobtrack.refresh-token')).toBeNull()
})

test('renders server-backed dashboard metrics and linked work items', async () => {
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/dashboard', () =>
      HttpResponse.json({
        ...emptyDashboard,
        company_count: 3,
        job_count: 5,
        application_status_counts: {
          ...emptyDashboard.application_status_counts,
          applied: 2,
          interview: 1,
          offer: 1,
          rejected: 1,
        },
        applications_last_7_days: 2,
        offer_conversion_rate: 0.25,
        upcoming_interviews: [
          {
            id: 31,
            application_id: 21,
            interview_type: 'technical',
            scheduled_at: '2026-09-25T04:00:00Z',
            duration_minutes: 60,
            application_summary: {
              id: 21,
              job_id: 11,
              status: 'interview',
              priority: 2,
              job_summary: {
                id: 11,
                company_id: 7,
                title: 'Backend Engineer',
                status: 'open',
                company_summary: { id: 7, name: 'Acme' },
              },
            },
          },
        ],
        overdue_actions: [
          {
            application_id: 22,
            job_id: 12,
            status: 'applied',
            next_action_at: '2026-09-23T04:00:00Z',
            job_summary: {
              id: 12,
              company_id: 8,
              title: 'Platform Engineer',
              status: 'open',
              company_summary: { id: 8, name: 'Globex' },
            },
          },
        ],
      }),
    ),
  )

  renderApp('/dashboard')

  expect(
    await screen.findByRole('heading', { name: '你好，joker' }),
  ).toBeInTheDocument()
  expect(screen.getByText('25%')).toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: /已申请：2 条投递/ }),
  ).toHaveAttribute('href', '/applications?status=applied')
  expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
  expect(screen.getByText(/Acme · 技术面试/)).toBeInTheDocument()
  expect(screen.getByText('Platform Engineer')).toBeInTheDocument()
  expect(screen.getByText(/Globex · 已申请/)).toBeInTheDocument()
})

function restoreSessionHandlers() {
  sessionStorage.setItem('jobtrack.refresh-token', 'stored-refresh')
  return [
    http.post('*/auth/refresh', () =>
      HttpResponse.json({
        access_token: 'restored-access',
        refresh_token: 'rotated-refresh',
        token_type: 'bearer',
      }),
    ),
    http.get('*/auth/me', () => HttpResponse.json(user)),
  ]
}

const company = {
  id: 7,
  name: 'Acme',
  website: 'https://acme.example.com/',
  industry: 'Technology',
  location: 'Shanghai',
  notes: 'Target company',
  created_at: '2026-09-24T00:00:00Z',
  updated_at: '2026-09-24T00:00:00Z',
}

test('creates a company and refreshes the company list', async () => {
  let items: (typeof company)[] = []
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/companies', () =>
      HttpResponse.json({ items, total: items.length, page: 1, page_size: 20 }),
    ),
    http.post('*/api/v1/companies', async ({ request }) => {
      expect(await request.json()).toMatchObject({ name: 'Acme' })
      items = [company]
      return HttpResponse.json(company, { status: 201 })
    }),
  )

  renderApp('/companies')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '＋ 新建公司' }))
  await actor.type(screen.getByLabelText('公司名称'), 'Acme')
  await actor.click(screen.getByRole('button', { name: '保存公司' }))

  expect(await screen.findByText('公司已创建。')).toBeInTheDocument()
  expect(await screen.findByRole('link', { name: /Acme/ })).toBeInTheDocument()
})

test('renders a job with its aggregated company summary', async () => {
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/jobs', () =>
      HttpResponse.json({
        items: [
          {
            id: 11,
            company_id: 7,
            title: 'Backend Engineer',
            employment_type: 'full_time',
            work_mode: 'hybrid',
            location: 'Shanghai',
            source: null,
            url: null,
            salary_min: 20000,
            salary_max: 30000,
            salary_currency: 'CNY',
            description: null,
            status: 'open',
            company_summary: { id: 7, name: 'Acme' },
            created_at: '2026-09-24T00:00:00Z',
            updated_at: '2026-09-24T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
      }),
    ),
  )

  renderApp('/jobs')
  expect(await screen.findAllByText('Backend Engineer')).not.toHaveLength(0)
  expect(screen.getAllByText('Acme')).not.toHaveLength(0)
})

test('keeps a company intact when dependent jobs cause a delete conflict', async () => {
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/companies/7', () => HttpResponse.json(company)),
    http.delete('*/api/v1/companies/7', () =>
      HttpResponse.json(
        { detail: 'Company cannot be deleted while it has jobs' },
        { status: 409 },
      ),
    ),
  )

  renderApp('/companies/7')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '删除' }))
  await actor.click(screen.getByRole('button', { name: '确认删除' }))

  expect(
    await screen.findByText('Company cannot be deleted while it has jobs'),
  ).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Acme' })).toBeInTheDocument()
})

const application = {
  id: 21,
  job_id: 11,
  status: 'saved' as string,
  priority: 2,
  applied_at: null as string | null,
  deadline: '2026-10-01',
  next_action_at: '2026-09-25T04:00:00Z',
  notes: 'Prepare tailored resume',
  created_at: '2026-09-24T00:00:00Z',
  updated_at: '2026-09-24T00:00:00Z',
  job_summary: {
    id: 11,
    company_id: 7,
    title: 'Backend Engineer',
    status: 'open' as const,
    company_summary: { id: 7, name: 'Acme' },
  },
}

test('offers only a legal next status and refreshes after server confirmation', async () => {
  let current = application
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/companies', () =>
      HttpResponse.json({
        items: [company],
        total: 1,
        page: 1,
        page_size: 100,
      }),
    ),
    http.get('*/api/v1/applications', () =>
      HttpResponse.json({ items: [current], total: 1, page: 1, page_size: 20 }),
    ),
    http.patch('*/api/v1/applications/21/status', async ({ request }) => {
      expect(await request.json()).toEqual({ status: 'applied' })
      current = {
        ...application,
        status: 'applied',
        applied_at: '2026-09-24',
      }
      return HttpResponse.json(current)
    }),
  )

  renderApp('/applications')
  const actor = userEvent.setup()
  expect(
    await screen.findByRole('button', { name: '转为已申请' }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: '转为Offer' }),
  ).not.toBeInTheDocument()
  await actor.click(screen.getByRole('button', { name: '转为已申请' }))

  expect(await screen.findByText('状态已更新为“已申请”。')).toBeInTheDocument()
  expect(await screen.findAllByText('已申请')).not.toHaveLength(0)
})

test('renders the server-backed application status timeline', async () => {
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/applications/21', () =>
      HttpResponse.json({
        ...application,
        status: 'screening',
        applied_at: '2026-09-24',
      }),
    ),
    http.get('*/api/v1/applications/21/history', () =>
      HttpResponse.json([
        {
          id: 1,
          application_id: 21,
          from_status: 'saved',
          to_status: 'applied',
          changed_at: '2026-09-24T01:00:00Z',
        },
        {
          id: 2,
          application_id: 21,
          from_status: 'applied',
          to_status: 'screening',
          changed_at: '2026-09-24T02:00:00Z',
        },
      ]),
    ),
  )

  renderApp('/applications/21')
  expect(
    await screen.findByRole('heading', { name: 'Backend Engineer' }),
  ).toBeInTheDocument()
  expect(screen.getByText('已收藏')).toBeInTheDocument()
  expect(screen.getAllByText('筛选中')).not.toHaveLength(0)
  expect(
    screen.getByRole('heading', { name: '状态时间线' }),
  ).toBeInTheDocument()
})

test('loads the visible calendar range and keeps an overlapping interview out', async () => {
  let rangeRequested = false
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/api/v1/interviews', ({ request }) => {
      const url = new URL(request.url)
      rangeRequested = Boolean(
        url.searchParams.get('scheduled_from') &&
        url.searchParams.get('scheduled_to'),
      )
      return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 100 })
    }),
    http.get('*/api/v1/applications', () =>
      HttpResponse.json({
        items: [
          {
            ...application,
            status: 'screening',
            applied_at: '2026-09-24',
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
      }),
    ),
    http.post('*/api/v1/interviews', async ({ request }) => {
      const body = (await request.json()) as { scheduled_at: string }
      expect(body.scheduled_at.endsWith('Z')).toBe(true)
      return HttpResponse.json(
        { detail: 'Interview overlaps another scheduled interview' },
        { status: 409 },
      )
    }),
  )

  renderApp('/interviews')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '＋ 安排面试' }))
  await actor.selectOptions(await screen.findByLabelText('投递'), '21')
  await actor.click(screen.getByRole('button', { name: '保存面试' }))

  expect(
    await screen.findByText('Interview overlaps another scheduled interview'),
  ).toBeInTheDocument()
  expect(rangeRequested).toBe(true)
  expect(screen.getByRole('dialog')).toBeInTheDocument()
})
const deviceSession = {
  id: '11111111-1111-4111-8111-111111111111',
  device_name: 'JobTrack Web · Linux',
  created_at: '2026-09-20T02:00:00Z',
  last_used_at: '2026-09-25T03:00:00Z',
  expires_at: '2026-10-25T03:00:00Z',
}

function securityHandlers({
  enabled = true,
  sessions = [deviceSession],
}: {
  enabled?: boolean
  sessions?: (typeof deviceSession)[]
} = {}) {
  return [
    ...restoreSessionHandlers(),
    http.get('*/auth/mfa/status', () =>
      HttpResponse.json({
        enabled,
        recovery_codes_remaining: enabled ? 7 : 0,
      }),
    ),
    http.get('*/auth/sessions', () => HttpResponse.json(sessions)),
  ]
}

test('shows the MFA status and server-backed device sessions', async () => {
  server.use(...securityHandlers())

  renderApp('/settings/security')

  expect(
    await screen.findByRole('heading', { name: '安全设置' }),
  ).toBeInTheDocument()
  expect(await screen.findByText('恢复码剩余 7 个')).toBeInTheDocument()
  expect(screen.getByText('JobTrack Web · Linux')).toBeInTheDocument()
  expect(screen.getByText(/后端不提供当前设备标识/)).toBeInTheDocument()
  expect(screen.queryByText('当前设备')).not.toBeInTheDocument()
})

test('enrolls TOTP locally and reveals one-time recovery codes', async () => {
  let enabled = false
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/auth/mfa/status', () =>
      HttpResponse.json({
        enabled,
        recovery_codes_remaining: enabled ? 2 : 0,
      }),
    ),
    http.get('*/auth/sessions', () => HttpResponse.json([])),
    http.post('*/auth/mfa/totp/enroll', async ({ request }) => {
      expect(await request.json()).toEqual({ password: 'correct-password' })
      return HttpResponse.json({
        secret: 'JBSWY3DPEHPK3PXP',
        provisioning_uri:
          'otpauth://totp/JobTrack:joker?secret=JBSWY3DPEHPK3PXP&issuer=JobTrack',
        expires_at: '2026-09-25T05:00:00Z',
      })
    }),
    http.post('*/auth/mfa/totp/confirm', async ({ request }) => {
      expect(await request.json()).toEqual({ code: '123456' })
      enabled = true
      return HttpResponse.json({
        recovery_codes: ['AAAA-BBBB-CCCC', 'DDDD-EEEE-FFFF'],
      })
    }),
  )

  renderApp('/settings/security')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '启用 MFA' }))
  await actor.type(screen.getByLabelText('当前密码'), 'correct-password')
  await actor.click(screen.getByRole('button', { name: '继续设置' }))

  expect(await screen.findByLabelText('MFA 设置二维码')).toBeInTheDocument()
  expect(screen.getByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument()
  await actor.type(screen.getByLabelText('6 位动态验证码'), '123456')
  await actor.click(screen.getByRole('button', { name: '确认并启用' }))

  expect(await screen.findByText('AAAA-BBBB-CCCC')).toBeInTheDocument()
  expect(screen.getByText('DDDD-EEEE-FFFF')).toBeInTheDocument()
  expect(screen.getByText(/关闭后无法再次查看/)).toBeInTheDocument()
})

test('revokes one device session after explicit confirmation', async () => {
  let sessions = [deviceSession]
  server.use(
    ...restoreSessionHandlers(),
    http.get('*/auth/mfa/status', () =>
      HttpResponse.json({ enabled: false, recovery_codes_remaining: 0 }),
    ),
    http.get('*/auth/sessions', () => HttpResponse.json(sessions)),
    http.delete('*/auth/sessions/:sessionId', ({ params }) => {
      expect(params.sessionId).toBe(deviceSession.id)
      sessions = []
      return HttpResponse.json({ message: 'Session revoked' })
    }),
  )

  renderApp('/settings/security')
  const actor = userEvent.setup()
  await screen.findByText('JobTrack Web · Linux')
  await actor.click(screen.getByRole('button', { name: '撤销' }))
  await actor.click(screen.getByRole('button', { name: '确认撤销' }))

  expect(await screen.findByText('没有活跃设备会话')).toBeInTheDocument()
  expect(screen.getByText('设备会话已撤销。')).toBeInTheDocument()
})

test('revokes every session and clears local authentication', async () => {
  server.use(
    ...securityHandlers(),
    http.delete('*/auth/sessions', () =>
      HttpResponse.json({ message: 'All sessions revoked' }),
    ),
  )

  renderApp('/settings/security')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '撤销全部会话' }))
  await actor.click(screen.getByRole('button', { name: '撤销全部并退出' }))

  expect(
    await screen.findByRole('heading', { name: '登录 JobTrack' }),
  ).toBeInTheDocument()
  expect(sessionStorage.getItem('jobtrack.refresh-token')).toBeNull()
})

test('keeps sensitive-operation fields after a server rejection', async () => {
  server.use(
    ...securityHandlers(),
    http.post('*/auth/mfa/recovery-codes/regenerate', () =>
      HttpResponse.json({ detail: 'Invalid MFA credential' }, { status: 400 }),
    ),
  )

  renderApp('/settings/security')
  const actor = userEvent.setup()
  await actor.click(await screen.findByRole('button', { name: '重置恢复码' }))
  const password = screen.getByLabelText('当前密码')
  const code = screen.getByLabelText('动态验证码')
  await actor.type(password, 'still-here')
  await actor.type(code, '654321')
  await actor.click(screen.getByRole('button', { name: '生成新恢复码' }))

  expect(await screen.findByText('Invalid MFA credential')).toBeInTheDocument()
  expect(password).toHaveValue('still-here')
  expect(code).toHaveValue('654321')
  expect(screen.getByRole('dialog')).toBeInTheDocument()
})
