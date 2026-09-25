export function Pagination({
  page,
  pageSize,
  total,
  onPage,
}: {
  page: number
  pageSize: number
  total: number
  onPage: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="mt-5 flex items-center justify-between text-sm">
      <p className="text-slate-500">
        共 {total} 条 · 第 {page}/{pages} 页
      </p>
      <div className="flex gap-2">
        <button
          className="button-secondary"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          上一页
        </button>
        <button
          className="button-secondary"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          下一页
        </button>
      </div>
    </div>
  )
}
