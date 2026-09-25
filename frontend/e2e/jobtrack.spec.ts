import { expect, test } from '@playwright/test'
import type { Page, TestInfo } from '@playwright/test'

test.setTimeout(90_000)

test('registers, manages the core pipeline, advances status, and logs out', async ({
  page,
}, testInfo) => {
  const suffix = `${Date.now()}_${testInfo.workerIndex}`
  const username = `e2e_${suffix}`
  const password = 'JobTrackE2E123!'
  const company = `E2E Company ${suffix}`
  const job = `E2E Backend Engineer ${suffix}`

  await page.goto('/register')
  await page.getByLabel('用户名').fill(username)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '创建账号' }).click()

  await expect(
    page.getByRole('heading', { name: '登录 JobTrack' }),
  ).toBeVisible()
  await page.getByLabel('用户名').fill(username)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(
    page.getByRole('heading', { name: `你好，${username}` }),
  ).toBeVisible()

  await page.getByRole('link', { name: '公司', exact: true }).click()
  await page.getByRole('button', { name: '＋ 新建公司' }).click()
  await page.getByLabel('公司名称').fill(company)
  await page.getByRole('button', { name: '保存公司' }).click()
  await expect(page.getByText('公司已创建。')).toBeVisible()
  await expect(
    page.getByRole('cell', { name: company, exact: true }),
  ).toBeVisible()

  await page.getByRole('link', { name: '职位', exact: true }).click()
  await page.getByRole('button', { name: '＋ 新建职位' }).click()
  const jobDialog = page.getByRole('dialog')
  await jobDialog.getByLabel('公司').selectOption({ label: company })
  await jobDialog.getByLabel('职位名称').fill(job)
  await jobDialog.getByLabel('办公方式').selectOption('remote')
  await page.getByRole('button', { name: '保存职位' }).click()
  await expect(page.getByText('职位已创建。')).toBeVisible()
  await expect(page.getByRole('cell', { name: job, exact: true })).toBeVisible()

  await page.getByRole('link', { name: '投递', exact: true }).click()
  await page.getByRole('button', { name: '＋ 新建投递' }).click()
  await page
    .getByRole('dialog')
    .getByRole('combobox', { name: '职位', exact: true })
    .selectOption({ index: 1 })
  await page.getByRole('button', { name: '保存投递' }).click()
  await expect(page.getByText('投递已创建。')).toBeVisible()
  const applicationCard = page.getByRole('article').filter({
    has: page.getByRole('heading', { name: job, exact: true }),
  })
  await expect(
    applicationCard.getByRole('heading', { name: job, exact: true }),
  ).toBeVisible()

  await applicationCard.getByRole('button', { name: '转为已申请' }).click()
  await expect(page.getByText('状态已更新为“已申请”。')).toBeVisible()

  await applicationCard.getByRole('link').click()
  await expect(page.getByRole('heading', { name: job })).toBeVisible()
  const timeline = page
    .getByRole('heading', { name: '状态时间线' })
    .locator('..')
  await expect(timeline.getByText('已收藏')).toBeVisible()
  await expect(timeline.getByText('已申请')).toBeVisible()

  await page.getByRole('button', { name: '退出' }).click()
  await page.getByRole('button', { name: '确认退出' }).click()
  await expect(
    page.getByRole('heading', { name: '登录 JobTrack' }),
  ).toBeVisible()
})

type TestIdentity = {
  username: string
  password: string
}

function identity(testInfo: TestInfo, label: string): TestIdentity {
  return {
    username: 'e2e_' + label + '_' + Date.now() + '_' + testInfo.workerIndex,
    password: 'JobTrackE2E123!',
  }
}

async function registerAccount(page: Page, account: TestIdentity) {
  await page.goto('/register')
  await page.getByLabel('用户名').fill(account.username)
  await page.getByLabel('密码').fill(account.password)
  await page.getByRole('button', { name: '创建账号' }).click()
  await expect(
    page.getByRole('heading', { name: '登录 JobTrack' }),
  ).toBeVisible()
}

async function loginAccount(page: Page, account: TestIdentity) {
  await page.getByLabel('用户名').fill(account.username)
  await page.getByLabel('密码').fill(account.password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(
    page.getByRole('heading', { name: '你好，' + account.username }),
  ).toBeVisible()
}

async function registerAndLogin(page: Page, testInfo: TestInfo, label: string) {
  const account = identity(testInfo, label)
  await registerAccount(page, account)
  await loginAccount(page, account)
  return account
}

async function navigateTo(page: Page, label: string) {
  const mobileMenu = page.getByRole('button', { name: '打开导航' })
  if (await mobileMenu.isVisible()) await mobileMenu.click()
  await page.getByRole('link', { name: label, exact: true }).click()
}

async function createTrackedApplication(
  page: Page,
  suffix: string,
): Promise<{
  company: string
  companyId: number
  job: string
  jobId: number
  applicationId: number
}> {
  const company = 'E2E Company ' + suffix
  const job = 'E2E Engineer ' + suffix

  await navigateTo(page, '公司')
  await page.getByRole('button', { name: '＋ 新建公司' }).click()
  await page.getByLabel('公司名称').fill(company)
  const companyResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/companies'),
  )
  await page.getByRole('button', { name: '保存公司' }).click()
  const companyId = ((await (await companyResponse).json()) as { id: number })
    .id
  await expect(page.getByText('公司已创建。')).toBeVisible()

  await navigateTo(page, '职位')
  await page.getByRole('button', { name: '＋ 新建职位' }).click()
  const jobDialog = page.getByRole('dialog')
  await jobDialog.getByLabel('公司').selectOption({ label: company })
  await jobDialog.getByLabel('职位名称').fill(job)
  await jobDialog.getByLabel('办公方式').selectOption('remote')
  const jobResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/jobs'),
  )
  await page.getByRole('button', { name: '保存职位' }).click()
  const jobId = ((await (await jobResponse).json()) as { id: number }).id
  await expect(page.getByText('职位已创建。')).toBeVisible()

  await navigateTo(page, '投递')
  await page.getByRole('button', { name: '＋ 新建投递' }).click()
  await page
    .getByRole('dialog')
    .getByRole('combobox', { name: '职位', exact: true })
    .selectOption({ index: 1 })
  const applicationResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/applications'),
  )
  await page.getByRole('button', { name: '保存投递' }).click()
  const applicationId = (
    (await (await applicationResponse).json()) as { id: number }
  ).id
  await expect(page.getByText('投递已创建。')).toBeVisible()

  return { company, companyId, job, jobId, applicationId }
}

test('refreshes exactly once after an access-token 401', async ({
  page,
}, testInfo) => {
  const account = identity(testInfo, 'refresh_once')
  await registerAccount(page, account)

  let dashboardAttempts = 0
  let refreshRequests = 0
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/auth/refresh')
      refreshRequests += 1
  })
  await page.route('**/api/v1/dashboard**', async (route) => {
    dashboardAttempts += 1
    if (dashboardAttempts === 1) {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Expired access token' }),
      })
      return
    }
    await route.continue()
  })

  await loginAccount(page, account)
  await expect.poll(() => dashboardAttempts).toBe(2)
  expect(refreshRequests).toBe(1)
})

test('returns to login without a refresh loop when refresh is invalid', async ({
  page,
}, testInfo) => {
  await registerAndLogin(page, testInfo, 'invalid_refresh')

  let refreshRequests = 0
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/auth/refresh')
      refreshRequests += 1
  })
  await page.evaluate(() => {
    sessionStorage.setItem('jobtrack.refresh-token', 'invalid-refresh-token')
  })
  await page.reload()

  await expect(
    page.getByRole('heading', { name: '登录 JobTrack' }),
  ).toBeVisible()
  await expect
    .poll(() =>
      page.evaluate(() => sessionStorage.getItem('jobtrack.refresh-token')),
    )
    .toBeNull()
  expect(refreshRequests).toBe(1)
})

test('keeps companies and jobs when dependent records block deletion', async ({
  page,
}, testInfo) => {
  const account = await registerAndLogin(page, testInfo, 'delete_conflict')
  const records = await createTrackedApplication(page, account.username)

  await page.goto('/companies/' + records.companyId)
  await expect(
    page.getByRole('heading', { name: records.company }),
  ).toBeVisible()
  await page.getByRole('button', { name: '删除', exact: true }).click()
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: '确认删除' })
    .click()
  await expect(
    page.getByRole('status').filter({
      hasText: 'Company cannot be deleted while it has jobs',
    }),
  ).toBeVisible()
  await expect(
    page.getByRole('heading', { name: records.company }),
  ).toBeVisible()

  await page.goto('/jobs/' + records.jobId)
  await expect(page.getByRole('heading', { name: records.job })).toBeVisible()
  await page.getByRole('button', { name: '删除', exact: true }).click()
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: '确认删除' })
    .click()
  await expect(
    page.getByRole('status').filter({
      hasText: 'Job cannot be deleted while it has applications',
    }),
  ).toBeVisible()
  await expect(page.getByRole('heading', { name: records.job })).toBeVisible()
})

test('creates an interview on mobile and preserves an overlapping form', async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const account = await registerAndLogin(page, testInfo, 'mobile_interview')
  const records = await createTrackedApplication(page, account.username)

  await page.getByRole('button', { name: '转为已申请' }).click()
  await expect(page.getByText('状态已更新为“已申请”。')).toBeVisible()
  await page.getByRole('button', { name: '转为筛选中' }).click()
  await expect(page.getByText('状态已更新为“筛选中”。')).toBeVisible()

  await navigateTo(page, '面试')
  await expect(page.getByRole('heading', { name: '面试日历' })).toBeVisible()
  await page.getByRole('button', { name: '＋ 安排面试' }).click()
  const firstDialog = page.getByRole('dialog')
  await firstDialog
    .getByRole('combobox', { name: '投递', exact: true })
    .selectOption({ index: 1 })
  const scheduledAt = await firstDialog.getByLabel('开始时间').inputValue()
  await firstDialog.getByRole('button', { name: '保存面试' }).click()

  await expect(page.getByText('面试已创建。')).toBeVisible()
  await expect(
    page.getByText('技术面试 · ' + records.company, { exact: true }),
  ).toBeVisible()

  await page.getByRole('button', { name: '＋ 安排面试' }).click()
  const overlapDialog = page.getByRole('dialog')
  const applicationSelect = overlapDialog.getByRole('combobox', {
    name: '投递',
    exact: true,
  })
  await applicationSelect.selectOption({ index: 1 })
  await overlapDialog.getByLabel('开始时间').fill(scheduledAt)
  await overlapDialog.getByRole('button', { name: '保存面试' }).click()

  await expect(
    overlapDialog.getByRole('alert').filter({
      hasText: 'Interview overlaps another scheduled interview',
    }),
  ).toBeVisible()
  await expect(overlapDialog.getByLabel('开始时间')).toHaveValue(scheduledAt)
  await expect(applicationSelect).not.toHaveValue('')
})
