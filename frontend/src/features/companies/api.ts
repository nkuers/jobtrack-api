import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components, operations } from '@/api/schema'

export type Company = components['schemas']['CompanyResponse']
export type CompanyInput = components['schemas']['CompanyCreate']
export type CompanyUpdate = components['schemas']['CompanyUpdate']
export type CompanyFilters = NonNullable<
  operations['list_companies_api_v1_companies_get']['parameters']['query']
>

export async function listCompanies(filters: CompanyFilters) {
  const { data, error, response } = await apiClient.GET('/api/v1/companies', {
    params: { query: filters },
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function getCompany(id: number) {
  const { data, error, response } = await apiClient.GET(
    '/api/v1/companies/{company_id}',
    { params: { path: { company_id: id } } },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function createCompany(body: CompanyInput) {
  const { data, error, response } = await apiClient.POST('/api/v1/companies', {
    body,
  })
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function updateCompany(id: number, body: CompanyUpdate) {
  const { data, error, response } = await apiClient.PATCH(
    '/api/v1/companies/{company_id}',
    { params: { path: { company_id: id } }, body },
  )
  if (!response.ok || !data) throw apiError(response, error)
  return data
}

export async function deleteCompany(id: number) {
  const { error, response } = await apiClient.DELETE(
    '/api/v1/companies/{company_id}',
    { params: { path: { company_id: id } } },
  )
  if (!response.ok) throw apiError(response, error)
}
