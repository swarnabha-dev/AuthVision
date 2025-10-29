"""
Stream-related Pydantic v2 models with strict typing.
"""

from pydantic import BaseModel, ConfigDict, Field


class StreamStartRequest(BaseModel):
    """Request to start an RTSP stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Unique camera identifier", min_length=1)
    rtsp_url: str | None = Field(
        default=None,
        description="RTSP stream URL (optional if using auto_discover)",
    )
    config_name: str = Field(
        default="default", description="Configuration profile name"
    )
    auto_discover: bool = Field(
        default=False,
        description="Auto-discover camera if rtsp_url not provided",
    )
    discovery_network: str = Field(
        default="192.168.1.0/24",
        description="Network to scan for auto-discovery",
    )
    priority: str = Field(
        default="medium",
        description="Stream priority (low/medium/high/critical)",
    )


class StreamStartResponse(BaseModel):
    """Response after starting a stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Camera identifier")
    started: bool = Field(..., description="Whether stream started successfully")
    message: str = Field(..., description="Status message")
    rtsp_url: str | None = Field(
        default=None, description="Actual RTSP URL used (if discovered)"
    )
    discovered: bool = Field(
        default=False, description="Whether URL was auto-discovered"
    )


class StreamStopRequest(BaseModel):
    """Request to stop an RTSP stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Unique camera identifier", min_length=1)


class StreamStopResponse(BaseModel):
    """Response after stopping a stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Camera identifier")
    stopped: bool = Field(..., description="Whether stream stopped successfully")


class AutoDiscoverRequest(BaseModel):
    """Request for automatic camera discovery."""

    model_config = ConfigDict(strict=True)

    network: str = Field(
        default="192.168.1.0/24",
        description="Network to scan in CIDR notation",
    )
    timeout: float = Field(
        default=2.0, description="Connection timeout in seconds", gt=0.0, le=10.0
    )
    max_cameras: int = Field(
        default=20, description="Maximum cameras to discover", gt=0, le=100
    )
    auto_start: bool = Field(
        default=False,
        description="Automatically start streams for discovered cameras",
    )


class AutoDiscoverResponse(BaseModel):
    """Response from automatic camera discovery."""

    model_config = ConfigDict(strict=True)

    cameras: list[dict[str, str]] = Field(description="List of discovered cameras")
    total_found: int = Field(description="Total cameras found", ge=0)
    auto_started: list[str] = Field(
        default=[], description="Camera IDs that were auto-started"
    )

