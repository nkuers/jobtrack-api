from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.admin import router as admin_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.email_verification import router as email_verification_router
from app.api.v1.health import router as health_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.mfa import router as mfa_router
from app.api.v1.oidc import router as oidc_router
from app.api.v1.password_reset import router as password_reset_router
from app.api.v1.sessions import router as sessions_router
from app.auth.login import router as login_router
from app.auth.register import router as register_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis_client
from app.core.tracing import setup_tracing, shutdown_tracing
from app.exceptions.handlers import register_exception_handlers
from app.middlewares.cors import setup_cors
from app.middlewares.rate_limit import setup_rate_limit
from app.middlewares.request_logging import setup_request_logging
from app.middlewares.security_headers import setup_security_headers
from jobtrack_api import __version__

setup_logging()  # 应用启动前准备日志，统一输出格式，方便调试


# 生命周期钩子：服务启动和关闭时该干嘛
@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        shutdown_tracing()
        await close_redis_client()


app = FastAPI(
    title=settings.APP_NAME,
    description="""
JobTrack API

A production-oriented job application tracking backend with:

- owner-scoped Companies and Jobs
- Applications with validated status transitions and history
- timezone-aware Interview scheduling and overlap detection
- Dashboard funnel metrics with resilient Redis caching
- JWT authentication, rotating refresh tokens, RBAC, and optional MFA/OIDC
- PostgreSQL transactions, Alembic migrations, and operational telemetry
""",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 把某种能力注册到服务上
setup_tracing(app)  # 链路追踪，用于线上排查性能

setup_cors(app)  # 浏览器跨域限制，用于前后端交互

setup_security_headers(app)  # 给HTTP响应头添加安全相关的字段，防止XSS、点击劫持等攻击

setup_rate_limit(app)  # 限流

setup_request_logging(app)  # 每个请求有唯一ID，方便排查问题

register_exception_handlers(app)  # 异常处理


app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(login_router)
app.include_router(register_router)
app.include_router(auth_router)
app.include_router(email_verification_router)
app.include_router(password_reset_router)
app.include_router(mfa_router)
app.include_router(oidc_router)
app.include_router(sessions_router)
app.include_router(admin_router)
app.include_router(companies_router)
app.include_router(jobs_router)
app.include_router(applications_router)
app.include_router(interviews_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {
        "message": "JobTrack API is running!",
        "version": __version__,
    }
