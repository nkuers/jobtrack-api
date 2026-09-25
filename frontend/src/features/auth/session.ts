import type { components } from '@/api/schema'

type Token = components['schemas']['Token']

const refreshTokenKey = 'jobtrack.refresh-token'
export const sessionExpiredEvent = 'jobtrack:session-expired'

let accessToken: string | null = null
let refreshPromise: Promise<boolean> | null = null

function apiOrigin() {
  return import.meta.env.VITE_API_BASE_URL || globalThis.location?.origin || ''
}

function storedRefreshToken() {
  if (typeof sessionStorage === 'undefined') return null
  return sessionStorage.getItem(refreshTokenKey)
}

export function hasRefreshToken() {
  return Boolean(storedRefreshToken())
}

export function setSession(tokens: Token) {
  accessToken = tokens.access_token
  sessionStorage.setItem(refreshTokenKey, tokens.refresh_token)
}

export function clearSession() {
  accessToken = null
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem(refreshTokenKey)
  }
}

export function currentRefreshToken() {
  return storedRefreshToken()
}

async function performRefresh(): Promise<boolean> {
  const refreshToken = storedRefreshToken()
  if (!refreshToken) return false

  try {
    const response = await globalThis.fetch(`${apiOrigin()}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    if (!response.ok) {
      clearSession()
      return false
    }

    const tokens = (await response.json()) as Token
    setSession(tokens)
    return true
  } catch {
    clearSession()
    return false
  }
}

export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = performRefresh().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function withAccessToken(request: Request) {
  const headers = new Headers(request.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  return new Request(request, { headers })
}

export const authenticatedFetch: typeof globalThis.fetch = async (
  input,
  init,
) => {
  const original = new Request(input, init)
  const retryRequest = original.clone()
  const response = await globalThis.fetch(withAccessToken(original))

  if (response.status !== 401 || !hasRefreshToken()) return response

  if (await refreshSession()) {
    return globalThis.fetch(withAccessToken(retryRequest))
  }

  globalThis.dispatchEvent?.(new CustomEvent(sessionExpiredEvent))
  return response
}

export function resetSessionForTests() {
  accessToken = null
  refreshPromise = null
  if (typeof sessionStorage !== 'undefined') sessionStorage.clear()
}
