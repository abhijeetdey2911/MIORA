"""Health check API endpoints."""

from fastapi import APIRouter, status
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="API v1 Health Check",
    description="Returns detailed health metrics including database connectivity and uptime.",
)
def get_v1_health() -> HealthResponse:
    """Retrieve system health and database connection status."""
    return HealthService.get_health_status()

