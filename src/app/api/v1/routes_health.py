"""
Health check routes.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends

from app.deps import AppConfig, get_config
from app.models.attendance_models import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])

# Track application start time
_start_time = time.time()


@router.get("", response_model=HealthResponse)
def health_check(config: AppConfig = Depends(get_config)) -> HealthResponse:
    """Get system health status.

    Args:
        config: Application configuration (injected)

    Returns:
        HealthResponse with current status
    """
    uptime = time.time() - _start_time
    return HealthResponse(
        status="healthy", timestamp=datetime.utcnow().isoformat() + "Z", uptime_seconds=uptime
    )
