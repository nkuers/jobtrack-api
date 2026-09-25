import { publicApiClient } from './client'

export async function getApiHealth() {
  const { data, error, response } = await publicApiClient.GET('/health/live')

  if (!response.ok || error) {
    throw new Error(
      `API health check failed with status ${response.status}: ${JSON.stringify(error)}`,
    )
  }

  return data
}
