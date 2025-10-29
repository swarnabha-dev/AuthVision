"""
Attendance-related Pydantic v2 models with strict typing.
"""

from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterRequest(BaseModel):
    """Request to register an edge device."""

    model_config = ConfigDict(strict=True)

    device_id: str = Field(..., description="Unique device identifier", min_length=1)
    model: str = Field(..., description="Device model name", min_length=1)
    location: str = Field(..., description="Physical location", min_length=1)


class DeviceRegisterResponse(BaseModel):
    """Response after device registration."""

    model_config = ConfigDict(strict=True)

    device_id: str = Field(..., description="Device identifier")
    status: str = Field(..., description="Registration status")
    registered_at: str = Field(..., description="ISO 8601 timestamp")


class EnrollResponse(BaseModel):
    """Response after student enrollment."""

    model_config = ConfigDict(strict=True)

    student_id: str = Field(..., description="Student identifier")
    enrolled: bool = Field(..., description="Whether enrollment was successful")
    embedding_id: str = Field(..., description="Generated embedding identifier")


class AttendanceRecord(BaseModel):
    """Single attendance record."""

    model_config = ConfigDict(strict=True)

    student_id: str = Field(..., description="Student identifier")
    start_time: str = Field(..., description="Entry time (ISO 8601)")
    end_time: str | None = Field(None, description="Exit time (ISO 8601), None if still present")
    confidence: float = Field(..., description="Recognition confidence", ge=0.0, le=1.0)
    camera_id: str = Field(..., description="Camera that recorded this entry")


class AttendanceQueryResponse(BaseModel):
    """Response with attendance records."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Camera identifier")
    date: str = Field(..., description="Query date (YYYY-MM-DD)")
    records: list[AttendanceRecord] = Field(..., description="List of attendance records")


class HealthResponse(BaseModel):
    """System health check response."""

    model_config = ConfigDict(strict=True)

    status: str = Field(..., description="Health status (healthy/degraded/unhealthy)")
    timestamp: str = Field(..., description="Current timestamp (ISO 8601)")
    uptime_seconds: float = Field(..., description="System uptime in seconds", ge=0.0)
