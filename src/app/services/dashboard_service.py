from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_cache import DashboardCache


class DashboardService:
    def __init__(self, db: Session, cache: DashboardCache | None = None):
        self.repository = DashboardRepository(db)
        self.cache = cache or DashboardCache()

    def get(self, owner_id: int) -> DashboardResponse:
        cached = self.cache.read(owner_id)
        if cached.value is not None:
            return cached.value

        dashboard = self.repository.aggregate(owner_id, now=datetime.now(UTC))
        self.cache.write(owner_id, dashboard)
        return dashboard
