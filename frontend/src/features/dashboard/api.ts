import { apiClient } from '@/api/client'
import { apiError } from '@/api/errors'
import type { components } from '@/api/schema'

export type Dashboard = components['schemas']['DashboardResponse']

export const dashboardKey = ['dashboard'] as const

export async function getDashboard(): Promise<Dashboard> {
  const { data, error, response } = await apiClient.GET('/api/v1/dashboard')
  if (!response.ok || !data) throw apiError(response, error)
  return data
}
