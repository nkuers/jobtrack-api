import { EmptyState } from '@/components/shared/states'

export function PlaceholderPage({
  title,
  stage,
}: {
  title: string
  stage: string
}) {
  return (
    <div>
      <p className="section-kicker">{stage}</p>
      <h1 className="page-title">{title}</h1>
      <div className="mt-8">
        <EmptyState
          title={`${title}即将接入`}
          description={`路由、权限和响应式外壳已完成；具体业务能力将在阶段 ${stage} 实现。`}
        />
      </div>
    </div>
  )
}
