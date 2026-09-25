import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components } from '@/api/schema'

export type MfaEnrollment = components['schemas']['MFAEnrollmentResponse']
export type DeviceSession = components['schemas']['DeviceSession']

export async function getMfaStatus() {
  const { data, error, response } = await apiClient.GET('/auth/mfa/status')
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function enrollTotp(password: string) {
  const { data, error, response } = await apiClient.POST(
    '/auth/mfa/totp/enroll',
    { body: { password } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function confirmTotp(code: string) {
  const { data, error, response } = await apiClient.POST(
    '/auth/mfa/totp/confirm',
    { body: { code } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function regenerateRecoveryCodes(input: {
  password: string
  code: string
}) {
  const { data, error, response } = await apiClient.POST(
    '/auth/mfa/recovery-codes/regenerate',
    { body: input },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function disableMfa(input: { password: string; code: string }) {
  const { data, error, response } = await apiClient.POST('/auth/mfa/disable', {
    body: input,
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function listDeviceSessions() {
  const { data, error, response } = await apiClient.GET('/auth/sessions')
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function revokeDeviceSession(sessionId: string) {
  const { data, error, response } = await apiClient.DELETE(
    '/auth/sessions/{session_id}',
    { params: { path: { session_id: sessionId } } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function revokeAllDeviceSessions() {
  const { data, error, response } = await apiClient.DELETE('/auth/sessions')
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
