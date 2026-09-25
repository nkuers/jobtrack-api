import { apiClient, publicApiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components } from '@/api/schema'

import { currentRefreshToken } from './session'

export type Token = components['schemas']['Token']
export type User = components['schemas']['UserResponse']
export type MFAChallenge = components['schemas']['MFAChallengeResponse']
export type LoginResult = Token | MFAChallenge

function deviceName() {
  const platform = navigator.platform || 'Web browser'
  return `JobTrack Web · ${platform}`.slice(0, 120)
}

export async function login(username: string, password: string) {
  const { data, error, response } = await publicApiClient.POST('/login/', {
    body: { username, password, scope: '' },
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-Device-Name': deviceName(),
    },
    bodySerializer(body) {
      const values = new URLSearchParams()
      for (const [key, value] of Object.entries(body)) {
        if (value !== undefined && value !== null)
          values.set(key, String(value))
      }
      return values
    },
  })

  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function register(input: components['schemas']['UserCreate']) {
  const { data, error, response } = await publicApiClient.POST('/register/', {
    body: input,
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function verifyMfa(challengeToken: string, code: string) {
  const { data, error, response } = await publicApiClient.POST(
    '/auth/mfa/challenge/verify',
    { body: { challenge_token: challengeToken, code } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function getCurrentUser() {
  const { data, error, response } = await apiClient.GET('/auth/me')
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function revokeCurrentSession() {
  const refreshToken = currentRefreshToken()
  if (!refreshToken) return
  const { response } = await publicApiClient.POST('/auth/logout', {
    body: { refresh_token: refreshToken },
  })
  if (!response.ok && response.status !== 401) {
    throw apiError(response, undefined)
  }
}
