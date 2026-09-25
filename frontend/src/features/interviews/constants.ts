import type { InterviewStatus, InterviewType } from './api'

export const typeLabel: Record<InterviewType, string> = {
  phone_screen: '电话初筛',
  technical: '技术面试',
  behavioral: '行为面试',
  system_design: '系统设计',
  hiring_manager: '主管面试',
  onsite: '现场面试',
  other: '其他',
}
export const statusLabel: Record<InterviewStatus, string> = {
  scheduled: '已安排',
  completed: '已完成',
  cancelled: '已取消',
}
export const typeColor: Record<InterviewType, string> = {
  phone_screen: '#0284c7',
  technical: '#7c3aed',
  behavioral: '#db2777',
  system_design: '#4f46e5',
  hiring_manager: '#0891b2',
  onsite: '#059669',
  other: '#64748b',
}

export function toLocalInput(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value)
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 16)
}
