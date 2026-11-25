from app.config import Settings
from app.models.health import HealthResponse


class HealthService:
    """Service layer for health-check operations."""

    VERSION = "0.2.0"

    @staticmethod
    def get_health(settings: Settings) -> HealthResponse:
        return HealthResponse(
            status="healthy",
            service=settings.app_name,
            environment=settings.app_env,
            version=HealthService.VERSION,
        )
