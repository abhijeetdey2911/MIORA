"""Health check service logic."""

import platform
import sys
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import check_db_connectivity
from app.schemas.health import (
    ApiHealth,
    DatabaseHealth,
    HealthResponse,
    ServiceHealthMap,
    SystemInfo,
)

# Record application startup timestamp
_START_TIME = time.time()


class HealthService:
    """Service to evaluate system and service health status."""

    @staticmethod
    def get_health_status() -> HealthResponse:
        """Run health checks across backend subsystems and return aggregated status."""
        uptime = round(time.time() - _START_TIME, 2)
        
        # Check database connectivity
        db_connected, db_latency, db_error = check_db_connectivity()
        
        db_health = DatabaseHealth(
            status="connected" if db_connected else "disconnected",
            latency_ms=db_latency,
            dialect=settings.SQLALCHEMY_DATABASE_URI.split(":")[0],
            error=db_error,
        )

        api_health = ApiHealth(
            status="operational",
            uptime_seconds=uptime,
        )

        # Overall status is degraded if database is down, healthy otherwise
        overall_status = "healthy" if db_connected else "degraded"

        return HealthResponse(
            status=overall_status,
            project=settings.PROJECT_NAME,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            timestamp=datetime.now(timezone.utc),
            services=ServiceHealthMap(
                database=db_health,
                api=api_health,
            ),
            system=SystemInfo(
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                environment=settings.ENVIRONMENT,
            ),
        )

