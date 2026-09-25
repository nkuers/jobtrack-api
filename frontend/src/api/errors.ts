export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type ErrorDetail =
  | string
  | { msg?: string; loc?: Array<string | number> }
  | Array<{ msg?: string; loc?: Array<string | number> }>
  | undefined

export function apiError(response: Response, payload: unknown): ApiError {
  const detail = (payload as { detail?: ErrorDetail } | undefined)?.detail
  let message = `请求失败（${response.status}）`

  if (typeof detail === 'string') {
    message = detail
  } else if (Array.isArray(detail)) {
    message = detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join('；')
  } else if (detail?.msg) {
    message = detail.msg
  }

  return new ApiError(
    message,
    response.status,
    response.headers.get('x-request-id') ?? undefined,
  )
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fallback =
      error.status === 429
        ? '操作过于频繁，请稍后重试。'
        : error.status === 503
          ? '服务暂时不可用，请稍后重试。'
          : error.message
    return error.requestId
      ? `${fallback}（请求 ID：${error.requestId}）`
      : fallback
  }
  return error instanceof Error ? error.message : '发生未知错误，请稍后重试。'
}
