import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components, operations } from '@/api/schema'

export type Application = components['schemas']['ApplicationResponse']
export type ApplicationInput = components['schemas']['ApplicationCreate']
export type ApplicationUpdate = components['schemas']['ApplicationUpdate']
export type ApplicationStatus = components['schemas']['ApplicationStatus']
export type ApplicationHistory =
  components['schemas']['ApplicationStatusHistoryResponse']
export type ApplicationFilters = NonNullable<
  operations['list_applications_api_v1_applications_get']['parameters']['query']
>

export const applicationKeys = {
  all: ['applications'] as const,
  list: (filters: object) => ['applications', 'list', filters] as const,
  detail: (id: number) => ['applications', 'detail', id] as const,
  history: (id: number) => ['applications', 'history', id] as const,
}

export async function listApplications(filters: ApplicationFilters) {
  const { data, error, response } = await apiClient.GET(
    '/api/v1/applications',
    { params: { query: filters } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function getApplication(id: number) {
  const { data, error, response } = await apiClient.GET(
    '/api/v1/applications/{application_id}',
    { params: { path: { application_id: id } } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function createApplication(body: ApplicationInput) {
  const { data, error, response } = await apiClient.POST(
    '/api/v1/applications',
    { body },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function updateApplication(id: number, body: ApplicationUpdate) {
  const { data, error, response } = await apiClient.PATCH(
    '/api/v1/applications/{application_id}',
    { params: { path: { application_id: id } }, body },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function changeApplicationStatus(
  id: number,
  status: ApplicationStatus,
) {
  const { data, error, response } = await apiClient.PATCH(
    '/api/v1/applications/{application_id}/status',
    { params: { path: { application_id: id } }, body: { status } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function listApplicationHistory(id: number) {
  const { data, error, response } = await apiClient.GET(
    '/api/v1/applications/{application_id}/history',
    { params: { path: { application_id: id } } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function deleteApplication(id: number) {
  const { error, response } = await apiClient.DELETE(
    '/api/v1/applications/{application_id}',
    { params: { path: { application_id: id } } },
  )
  if (!response.ok) throw apiError(response, error)
}
