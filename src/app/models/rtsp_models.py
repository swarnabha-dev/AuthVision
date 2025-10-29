"""
RTSP and frame acquisition models (Module 2).

Pydantic models for RTSP stream configuration, frame buffers, and BAFS scheduler.
Strictly typed with no typing.Any usage.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field


class StreamStatus(str, Enum):
    """RTSP stream status."""

    IDLE = "idle"
    CONNECTING = "connecting"
    ACTIVE = "active"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    STOPPED = "stopped"


class StreamPriority(str, Enum):
    """Stream priority levels for BAFS scheduling."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RTSPConfig(BaseModel):
    """RTSP stream configuration."""

    model_config = ConfigDict(strict=True, frozen=True)

    camera_id: str = Field(description="Unique camera identifier")
    rtsp_url: str = Field(description="RTSP stream URL")
    transport: str = Field(default="tcp", description="Transport protocol (tcp/udp)")
    timeout_ms: int = Field(default=5000, description="Connection timeout in ms", gt=0)
    reconnect_delay_ms: int = Field(
        default=2000, description="Delay before reconnection attempt", gt=0
    )
    max_reconnect_attempts: int = Field(
        default=5, description="Max reconnection attempts", gt=0
    )
    buffer_size: int = Field(default=10, description="Frame buffer size", gt=0, le=100)
    target_fps: float = Field(default=30.0, description="Target FPS", gt=0.0, le=60.0)
    priority: StreamPriority = Field(
        default=StreamPriority.MEDIUM, description="Stream priority"
    )


class FrameMetadata(BaseModel):
    """Metadata for a captured frame."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    camera_id: str = Field(description="Camera identifier")
    frame_id: int = Field(description="Sequential frame number", ge=0)
    timestamp: datetime = Field(description="Frame capture timestamp")
    width: int = Field(description="Frame width in pixels", gt=0)
    height: int = Field(description="Frame height in pixels", gt=0)
    channels: int = Field(description="Number of color channels", ge=1, le=4)
    fps: float = Field(description="Current FPS", ge=0.0)
    is_motion_detected: bool = Field(default=False, description="Motion detected flag")


class Frame(BaseModel):
    """A captured video frame with metadata."""

    model_config = ConfigDict(strict=True, arbitrary_types_allowed=True)

    metadata: FrameMetadata = Field(description="Frame metadata")
    data: Annotated[
        npt.NDArray[np.uint8], Field(description="Frame data as numpy array (H, W, C)")
    ]

    def __hash__(self) -> int:
        """Make Frame hashable for set/dict usage."""
        return hash((self.metadata.camera_id, self.metadata.frame_id))


class StreamStats(BaseModel):
    """Statistics for an RTSP stream."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(description="Camera identifier")
    status: StreamStatus = Field(description="Current stream status")
    uptime_seconds: float = Field(default=0.0, description="Stream uptime", ge=0.0)
    frames_captured: int = Field(default=0, description="Total frames captured", ge=0)
    frames_dropped: int = Field(default=0, description="Frames dropped", ge=0)
    current_fps: float = Field(default=0.0, description="Current FPS", ge=0.0)
    allocated_fps: float = Field(default=0.0, description="BAFS allocated FPS", ge=0.0)
    reconnect_count: int = Field(default=0, description="Reconnection attempts", ge=0)
    last_frame_time: datetime | None = Field(
        default=None, description="Last frame timestamp"
    )
    error_message: str | None = Field(default=None, description="Last error message")


class BAFSConfig(BaseModel):
    """BAFS (Budget-Aware Frame Scheduler) configuration."""

    model_config = ConfigDict(strict=True, frozen=True)

    total_fps_budget: float = Field(
        default=120.0, description="Total FPS budget across all streams", gt=0.0
    )
    min_fps_per_stream: float = Field(
        default=1.0, description="Minimum FPS per stream", gt=0.0, le=10.0
    )
    max_fps_per_stream: float = Field(
        default=30.0, description="Maximum FPS per stream", gt=0.0, le=60.0
    )
    motion_detection_enabled: bool = Field(
        default=True, description="Enable motion-based priority"
    )
    motion_fps_boost: float = Field(
        default=2.0, description="FPS multiplier on motion detection", ge=1.0, le=5.0
    )
    priority_weights: dict[StreamPriority, float] = Field(
        default={
            StreamPriority.LOW: 0.5,
            StreamPriority.MEDIUM: 1.0,
            StreamPriority.HIGH: 2.0,
            StreamPriority.CRITICAL: 4.0,
        },
        description="Priority-based FPS weights",
    )
    reallocation_interval_ms: int = Field(
        default=1000, description="FPS reallocation interval", gt=0
    )


class BAFSAllocation(BaseModel):
    """BAFS FPS allocation result."""

    model_config = ConfigDict(strict=True)

    camera_id: str = Field(description="Camera identifier")
    allocated_fps: float = Field(description="Allocated FPS", ge=0.0)
    priority: StreamPriority = Field(description="Stream priority")
    is_motion_active: bool = Field(description="Motion detected flag")
    allocation_timestamp: datetime = Field(description="Allocation time")


class StreamControlResponse(BaseModel):
    """Response for stream control operations."""

    model_config = ConfigDict(strict=True)

    success: bool = Field(description="Operation success flag")
    camera_id: str = Field(description="Camera identifier")
    message: str = Field(description="Status message")
    current_status: StreamStatus = Field(description="Stream status after operation")
