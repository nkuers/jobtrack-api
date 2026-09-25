import createClient from 'openapi-fetch'

import { authenticatedFetch } from '@/features/auth/session'

import type { paths } from './schema'

export const apiOrigin =
  import.meta.env.VITE_API_BASE_URL || globalThis.location?.origin || ''

export const apiClient = createClient<paths>({
  baseUrl: apiOrigin,
  fetch: authenticatedFetch,
})

export const publicApiClient = createClient<paths>({
  baseUrl: apiOrigin,
  fetch: (...arguments_) => globalThis.fetch(...arguments_),
})
