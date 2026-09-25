import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components, operations } from '@/api/schema'

export type Job = components['schemas']['JobResponse']
export type JobInput = components['schemas']['JobCreate']
export type JobUpdate = components['schemas']['JobUpdate']
export type JobFilters = NonNullable<
  operations['list_jobs_api_v1_jobs_get']['parameters']['query']
>

export async function listJobs(filters: JobFilters) {
  const { data, error, response } = await apiClient.GET('/api/v1/jobs', {
    params: { query: filters },
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function getJob(id: number) {
  const { data, error, response } = await apiClient.GET(
    '/api/v1/jobs/{job_id}',
    { params: { path: { job_id: id } } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function createJob(body: JobInput) {
  const { data, error, response } = await apiClient.POST('/api/v1/jobs', {
    body,
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function updateJob(id: number, body: JobUpdate) {
  const { data, error, response } = await apiClient.PATCH(
    '/api/v1/jobs/{job_id}',
    { params: { path: { job_id: id } }, body },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
export async function deleteJob(id: number) {
  const { error, response } = await apiClient.DELETE('/api/v1/jobs/{job_id}', {
    params: { path: { job_id: id } },
  })
  if (!response.ok) throw apiError(response, error)
}
