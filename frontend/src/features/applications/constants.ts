import type { ApplicationStatus } from './api'

export const applicationStatuses: ApplicationStatus[] = [
  'saved',
  'applied',
  'screening',
  'interview',
  'offer',
  'rejected',
  'withdrawn',
  'archived',
]
export const activeStatuses: ApplicationStatus[] = [
  'saved',
  'applied',
  'screening',
  'interview',
  'offer',
]
export const terminalStatuses: ApplicationStatus[] = [
  'rejected',
  'withdrawn',
  'archived',
]
export const statusLabel: Record<ApplicationStatus, string> = {
  saved: '已收藏',
  applied: '已申请',
  screening: '筛选中',
  interview: '面试中',
  offer: 'Offer',
  rejected: '已拒绝',
  withdrawn: '已撤回',
  archived: '已归档',
}
export const allowedTransitions: Record<
  ApplicationStatus,
  ApplicationStatus[]
> = {
  saved: ['applied', 'withdrawn'],
  applied: ['screening', 'rejected', 'withdrawn'],
  screening: ['interview', 'rejected', 'withdrawn'],
  interview: ['offer', 'rejected', 'withdrawn'],
  offer: ['archived'],
  rejected: ['archived'],
  withdrawn: ['archived'],
  archived: [],
}
export const statusTone: Record<ApplicationStatus, string> = {
  saved: 'app-saved',
  applied: 'app-applied',
  screening: 'app-screening',
  interview: 'app-interview',
  offer: 'app-offer',
  rejected: 'app-rejected',
  withdrawn: 'app-withdrawn',
  archived: 'app-archived',
}

export function formatLocalDateTime(value?: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN')
}
