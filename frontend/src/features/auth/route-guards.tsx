import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { PageSkeleton } from '@/components/shared/states'

import { useAuth } from './auth-context'

export function RequireAuth() {
  const { user, isInitializing } = useAuth()
  const location = useLocation()
  if (isInitializing) return <PageSkeleton />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

export function RequireGuest() {
  const { user, isInitializing } = useAuth()
  if (isInitializing) return <PageSkeleton />
  if (user) return <Navigate to="/dashboard" replace />
  return <Outlet />
}
