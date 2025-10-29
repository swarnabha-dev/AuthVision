"""
Dependency injection providers for FastAPI.
"""

from app.models.config import AppConfig, get_config
from app.services.attendance_service import AttendanceService, get_attendance_service
from app.services.stream_service import StreamService, get_stream_service

__all__ = [
    "get_config",
    "get_stream_service",
    "get_attendance_service",
    "AppConfig",
    "StreamService",
    "AttendanceService",
]
