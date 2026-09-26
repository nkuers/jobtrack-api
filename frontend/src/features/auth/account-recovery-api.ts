import { publicApiClient } from '@/api/client'
import { apiError } from '@/api/errors'

export async function requestEmailVerification(email: string) {
  const { data, error, response } = await publicApiClient.POST(
    '/auth/email-verification/request',
    { body: { email } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function confirmEmailVerification(token: string) {
  const { data, error, response } = await publicApiClient.POST(
    '/auth/email-verification/confirm',
    { body: { token } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function requestPasswordReset(email: string) {
  const { data, error, response } = await publicApiClient.POST(
    '/auth/password-reset/request',
    { body: { email } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function confirmPasswordReset(token: string, newPassword: string) {
  const { data, error, response } = await publicApiClient.POST(
    '/auth/password-reset/confirm',
    { body: { token, new_password: newPassword } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
