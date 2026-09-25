import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components, operations } from '@/api/schema'

export type Interview = components['schemas']['InterviewResponse']
export type InterviewInput = components['schemas']['InterviewCreate']
export type InterviewUpdate = components['schemas']['InterviewUpdate']
export type InterviewStatus = components['schemas']['InterviewStatus']
export type InterviewType = components['schemas']['InterviewType']
export type InterviewFilters = NonNullable<
  operations['list_interviews_api_v1_interviews_get']['parameters']['query']
>
export const interviewKeys = {
  all: ['interviews'] as const,
  range: (filters: object) => ['interviews', 'range', filters] as const,
}

export async function listInterviews(filters: InterviewFilters) {
  const { data, error, response } = await apiClient.GET('/api/v1/interviews', {
    params: { query: filters },
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function createInterview(body: InterviewInput) {
  const { data, error, response } = await apiClient.POST('/api/v1/interviews', {
    body,
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function updateInterview(id: number, body: InterviewUpdate) {
  const { data, error, response } = await apiClient.PATCH(
    '/api/v1/interviews/{interview_id}',
    { params: { path: { interview_id: id } }, body },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function deleteInterview(id: number) {
  const { error, response } = await apiClient.DELETE(
    '/api/v1/interviews/{interview_id}',
    { params: { path: { interview_id: id } } },
  )
  if (!response.ok) throw apiError(response, error)
}
