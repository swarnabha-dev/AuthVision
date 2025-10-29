"""
Stream-related Pydantic v2 models with strict typing.
"""

from pydantic import BaseModel, ConfigDict, Field


class StreamStartRequest(BaseModel):
    """Request to start an RTSP stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Unique camera identifier", min_length=1)
    rtsp_url: str = Field(..., description="RTSP stream URL", min_length=1)
    config_name: str = Field(..., description="Configuration profile name", min_length=1)


class StreamStartResponse(BaseModel):
    """Response after starting a stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Camera identifier")
    started: bool = Field(..., description="Whether stream started successfully")
    message: str = Field(..., description="Status message")


class StreamStopRequest(BaseModel):
    """Request to stop an RTSP stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Unique camera identifier", min_length=1)


class StreamStopResponse(BaseModel):
    """Response after stopping a stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(..., description="Camera identifier")
    stopped: bool = Field(..., description="Whether stream stopped successfully")
