from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return service health status."""
    return HealthService.get_health(settings)
