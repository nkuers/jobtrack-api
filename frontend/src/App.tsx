import { lazy, Suspense, type PropsWithChildren } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ErrorBoundary } from '@/components/shared/error-boundary'
import { PageSkeleton } from '@/components/shared/states'
import { AppShell } from '@/components/layout/app-shell'
import { LoginPage } from '@/features/auth/login-page'
import { MfaChallengePage } from '@/features/auth/mfa-challenge-page'
import { RegisterPage } from '@/features/auth/register-page'
import { RequireAuth, RequireGuest } from '@/features/auth/route-guards'
import { NotFoundPage } from '@/features/system/not-found-page'
import { PlaceholderPage } from '@/features/system/placeholder-page'

const DashboardPage = lazy(() =>
  import('@/features/dashboard/pages').then((module) => ({
    default: module.DashboardPage,
  })),
)

const ApplicationsPage = lazy(() =>
  import('@/features/applications/pages').then((module) => ({
    default: module.ApplicationsPage,
  })),
)
const ApplicationBoardPage = lazy(() =>
  import('@/features/applications/pages').then((module) => ({
    default: module.ApplicationBoardPage,
  })),
)
const ApplicationDetailPage = lazy(() =>
  import('@/features/applications/pages').then((module) => ({
    default: module.ApplicationDetailPage,
  })),
)
const CompaniesPage = lazy(() =>
  import('@/features/companies/pages').then((module) => ({
    default: module.CompaniesPage,
  })),
)
const CompanyDetailPage = lazy(() =>
  import('@/features/companies/pages').then((module) => ({
    default: module.CompanyDetailPage,
  })),
)
const JobsPage = lazy(() =>
  import('@/features/jobs/pages').then((module) => ({
    default: module.JobsPage,
  })),
)
const JobDetailPage = lazy(() =>
  import('@/features/jobs/pages').then((module) => ({
    default: module.JobDetailPage,
  })),
)

const InterviewsPage = lazy(() =>
  import('@/features/interviews/page').then((module) => ({
    default: module.InterviewsPage,
  })),
)

const SecurityPage = lazy(() =>
  import('@/features/settings/security-page').then((module) => ({
    default: module.SecurityPage,
  })),
)

function Deferred({ children }: PropsWithChildren) {
  return <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<RequireGuest />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/mfa/challenge" element={<MfaChallengePage />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route
            path="/dashboard"
            element={
              <Deferred>
                <DashboardPage />
              </Deferred>
            }
          />
          <Route
            path="/applications"
            element={
              <Deferred>
                <ApplicationsPage />
              </Deferred>
            }
          />
          <Route
            path="/applications/board"
            element={
              <Deferred>
                <ApplicationBoardPage />
              </Deferred>
            }
          />
          <Route
            path="/applications/:id"
            element={
              <Deferred>
                <ApplicationDetailPage />
              </Deferred>
            }
          />
          <Route
            path="/interviews"
            element={
              <Deferred>
                <InterviewsPage />
              </Deferred>
            }
          />
          <Route
            path="/jobs"
            element={
              <Deferred>
                <JobsPage />
              </Deferred>
            }
          />
          <Route
            path="/jobs/:id"
            element={
              <Deferred>
                <JobDetailPage />
              </Deferred>
            }
          />
          <Route
            path="/companies"
            element={
              <Deferred>
                <CompaniesPage />
              </Deferred>
            }
          />
          <Route
            path="/companies/:id"
            element={
              <Deferred>
                <CompanyDetailPage />
              </Deferred>
            }
          />
          <Route
            path="/settings/security"
            element={
              <Deferred>
                <SecurityPage />
              </Deferred>
            }
          />
          <Route
            path="/settings/*"
            element={<PlaceholderPage title="账号设置" stage="F7" />}
          />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ErrorBoundary>
  )
}
