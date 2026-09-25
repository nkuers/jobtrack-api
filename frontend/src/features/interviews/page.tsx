import FullCalendar, {
  type DateClickInfo,
  type DatesSetInfo,
  type EventClickInfo,
  type EventInput,
} from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/react/daygrid'
import interactionPlugin from '@fullcalendar/react/interaction'
import listPlugin from '@fullcalendar/react/list'
import zhCnLocale from '@fullcalendar/react/locales/zh-cn'
import themePlugin from '@fullcalendar/react/themes/breezy'
import '@fullcalendar/react/skeleton.css'
import '@fullcalendar/react/themes/breezy/theme.css'
import '@fullcalendar/react/themes/breezy/palettes/emerald.css'
import timeGridPlugin from '@fullcalendar/react/timegrid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { errorMessage } from '@/api/errors'
import { EmptyState } from '@/components/shared/states'
import { ConfirmDialog } from '@/components/ui/confirm-dialog'
import { Modal } from '@/components/ui/modal'
import { useToast } from '@/components/ui/toast'
import { listApplications } from '@/features/applications/api'

import {
  createInterview,
  deleteInterview,
  interviewKeys,
  listInterviews,
  updateInterview,
  type Interview,
  type InterviewInput,
  type InterviewStatus,
  type InterviewUpdate,
} from './api'
import { statusLabel, typeColor, typeLabel } from './constants'
import { InterviewForm } from './interview-form'

type Range = { start: string; end: string }
const eligibleStatuses = new Set(['screening', 'interview', 'offer'])

export function InterviewsPage() {
  const [range, setRange] = useState<Range | null>(null)
  const [status, setStatus] = useState<InterviewStatus | ''>('')
  const [createOpen, setCreateOpen] = useState(false)
  const [initialDate, setInitialDate] = useState<Date>()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const filters = {
    scheduled_from: range?.start,
    scheduled_to: range?.end,
    status: status || undefined,
    page_size: 100,
  }
  const interviews = useQuery({
    queryKey: interviewKeys.range(filters),
    queryFn: () => listInterviews(filters),
    enabled: Boolean(range),
  })
  const applications = useQuery({
    queryKey: ['applications', 'interview-options'],
    queryFn: () =>
      listApplications({
        page_size: 100,
        sort_by: 'updated_at',
        sort_order: 'desc',
      }),
    enabled: createOpen,
  })
  const eligibleApplications =
    applications.data?.items.filter((item) =>
      eligibleStatuses.has(item.status),
    ) || []
  const selected = interviews.data?.items.find((item) => item.id === selectedId)
  const client = useQueryClient()
  const { showToast } = useToast()
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({ queryKey: interviewKeys.all }),
      client.invalidateQueries({ queryKey: ['dashboard'] }),
    ])
  const create = useMutation({
    mutationFn: (input: InterviewInput) => createInterview(input),
    onSuccess: async () => {
      await refresh()
      setCreateOpen(false)
      showToast('面试已创建。')
    },
  })
  const update = useMutation({
    mutationFn: ({ id, input }: { id: number; input: InterviewUpdate }) =>
      updateInterview(id, input),
    onSuccess: async () => {
      await refresh()
      setEditing(false)
      showToast('面试已更新。')
    },
  })
  const remove = useMutation({
    mutationFn: (id: number) => deleteInterview(id),
    onSuccess: async () => {
      await refresh()
      setDeleteOpen(false)
      setSelectedId(null)
      showToast('面试已删除。')
    },
  })
  const events = useMemo<EventInput[]>(
    () =>
      (interviews.data?.items || []).map((item) => ({
        id: String(item.id),
        title: `${typeLabel[item.interview_type]} · ${item.application_summary.job_summary.company_summary.name}`,
        start: item.scheduled_at,
        end: new Date(
          new Date(item.scheduled_at).getTime() +
            item.duration_minutes * 60_000,
        ).toISOString(),
        color:
          item.status === 'cancelled'
            ? '#64748b'
            : item.status === 'completed'
              ? '#059669'
              : typeColor[item.interview_type],
        extendedProps: { status: item.status },
      })),
    [interviews.data],
  )

  function handleRange(info: DatesSetInfo) {
    const next = {
      start: info.start.toISOString(),
      end: info.end.toISOString(),
    }
    setRange((current) =>
      current?.start === next.start && current.end === next.end
        ? current
        : next,
    )
  }
  function handleDate(info: DateClickInfo) {
    setInitialDate(info.date)
    setCreateOpen(true)
  }
  function handleEvent(info: EventClickInfo) {
    setSelectedId(Number(info.event.id))
    setEditing(false)
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="section-kicker">日程管理</p>
          <h1 className="page-title">面试日历</h1>
          <p className="page-description">
            时间以浏览器本地时区显示，保存时统一转换为 UTC。
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="filter-input !min-w-32 !flex-none"
            aria-label="面试状态"
            value={status}
            onChange={(event) =>
              setStatus(event.target.value as InterviewStatus | '')
            }
          >
            <option value="">全部状态</option>
            <option value="scheduled">已安排</option>
            <option value="completed">已完成</option>
            <option value="cancelled">已取消</option>
          </select>
          <button
            className="button-primary"
            onClick={() => {
              setInitialDate(undefined)
              setCreateOpen(true)
            }}
          >
            ＋ 安排面试
          </button>
        </div>
      </div>
      {interviews.isError && (
        <div className="error-box mt-5">{errorMessage(interviews.error)}</div>
      )}
      {interviews.data && interviews.data.total > 100 && (
        <div className="mt-5 rounded-xl bg-amber-100 p-3 text-sm text-amber-800">
          当前范围超过 100 场面试，仅显示前 100 条。
        </div>
      )}
      <section
        className="calendar-shell mt-6"
        aria-busy={interviews.isFetching}
      >
        <FullCalendar
          plugins={[
            themePlugin,
            interactionPlugin,
            dayGridPlugin,
            timeGridPlugin,
            listPlugin,
          ]}
          locale={zhCnLocale}
          initialView={window.innerWidth < 768 ? 'listWeek' : 'dayGridMonth'}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek',
          }}
          events={events}
          datesSet={handleRange}
          dateClick={handleDate}
          eventClick={handleEvent}
          nowIndicator
          selectable
          dayMaxEvents
          height="auto"
          noEventsContent="当前范围没有面试"
        />
      </section>
      <Modal
        open={createOpen}
        title="安排面试"
        description="仅筛选中、面试中或已获 Offer 的投递可以安排面试。"
        onClose={() => setCreateOpen(false)}
      >
        {applications.isPending ? (
          <p>正在加载可用投递…</p>
        ) : applications.isError ? (
          <div className="error-box">{errorMessage(applications.error)}</div>
        ) : eligibleApplications.length === 0 ? (
          <div>
            <EmptyState
              title="没有可安排面试的投递"
              description="请先将投递推进到筛选、面试或 Offer 状态。"
            />
            <Link className="button-primary mt-4" to="/applications">
              前往投递管理
            </Link>
          </div>
        ) : (
          <InterviewForm
            applications={eligibleApplications}
            initialDate={initialDate}
            busy={create.isPending}
            onCancel={() => setCreateOpen(false)}
            onSubmit={async (input) => {
              await create.mutateAsync(input as InterviewInput)
            }}
          />
        )}
      </Modal>
      <Modal
        open={Boolean(selected)}
        title={selected ? typeLabel[selected.interview_type] : '面试详情'}
        onClose={() => {
          setSelectedId(null)
          setEditing(false)
        }}
      >
        {selected &&
          (editing ? (
            <InterviewForm
              interview={selected}
              busy={update.isPending}
              onCancel={() => setEditing(false)}
              onSubmit={async (input) => {
                await update.mutateAsync({
                  id: selected.id,
                  input: input as InterviewUpdate,
                })
              }}
            />
          ) : (
            <InterviewDetails
              interview={selected}
              onEdit={() => setEditing(true)}
              onDelete={() => setDeleteOpen(true)}
            />
          ))}
      </Modal>
      <ConfirmDialog
        open={deleteOpen}
        title="删除这场面试？"
        description="删除后无法恢复，但不会删除关联的投递。"
        busy={remove.isPending}
        confirmLabel="确认删除"
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() =>
          selected &&
          void remove
            .mutateAsync(selected.id)
            .catch((error) => showToast(errorMessage(error), 'error'))
        }
      />
    </div>
  )
}

function InterviewDetails({
  interview,
  onEdit,
  onDelete,
}: {
  interview: Interview
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`status-badge interview-${interview.status}`}>
          {statusLabel[interview.status]}
        </span>
        <span className="text-sm text-slate-500">
          {interview.application_summary.job_summary.company_summary.name} ·{' '}
          {interview.application_summary.job_summary.title}
        </span>
      </div>
      <dl className="detail-grid mt-5">
        <div>
          <dt>开始时间</dt>
          <dd>{new Date(interview.scheduled_at).toLocaleString('zh-CN')}</dd>
        </div>
        <div>
          <dt>时长</dt>
          <dd>{interview.duration_minutes} 分钟</dd>
        </div>
        <div>
          <dt>地点</dt>
          <dd>{interview.location || '—'}</dd>
        </div>
        <div>
          <dt>会议链接</dt>
          <dd>
            {interview.meeting_url ? (
              <a
                className="text-link"
                href={interview.meeting_url}
                target="_blank"
                rel="noreferrer"
              >
                加入会议
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt>准备笔记</dt>
          <dd className="whitespace-pre-wrap">{interview.notes || '—'}</dd>
        </div>
        {interview.feedback && (
          <div className="sm:col-span-2">
            <dt>面试反馈</dt>
            <dd className="whitespace-pre-wrap">{interview.feedback}</dd>
          </div>
        )}
      </dl>
      <div className="mt-5 flex justify-end gap-2">
        <button className="button-danger" onClick={onDelete}>
          删除
        </button>
        <button className="button-primary" onClick={onEdit}>
          编辑与更新状态
        </button>
      </div>
    </div>
  )
}
