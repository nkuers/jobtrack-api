import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import {
  afterAll,
  afterEach,
  beforeAll,
  beforeEach,
  expect,
  test,
} from 'vitest'

import { authenticatedFetch, resetSessionForTests, setSession } from './session'

let refreshCount = 0
let resourceCount = 0
const server = setupServer(
  http.post('*/auth/refresh', () => {
    refreshCount += 1
    return HttpResponse.json({
      access_token: 'new-access',
      refresh_token: 'new-refresh',
      token_type: 'bearer',
    })
  }),
  http.get('*/protected-resource', ({ request }) => {
    resourceCount += 1
    if (request.headers.get('authorization') !== 'Bearer new-access') {
      return new HttpResponse(null, { status: 401 })
    }
    return HttpResponse.json({ ok: true })
  }),
)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => {
  resetSessionForTests()
  refreshCount = 0
  resourceCount = 0
})
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

test('shares one rotating refresh request across concurrent 401 responses', async () => {
  setSession({
    access_token: 'expired',
    refresh_token: 'old-refresh',
    token_type: 'bearer',
  })
  const responses = await Promise.all([
    authenticatedFetch('http://localhost:3000/protected-resource'),
    authenticatedFetch('http://localhost:3000/protected-resource'),
  ])

  expect(responses.every((response) => response.ok)).toBe(true)
  expect(refreshCount).toBe(1)
  expect(resourceCount).toBe(4)
  expect(sessionStorage.getItem('jobtrack.refresh-token')).toBe('new-refresh')
})
