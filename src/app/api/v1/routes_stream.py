"""
Stream management routes (Module 2: RTSP + BAFS integration).
"""

from fastapi import APIRouter, Depends

from app.deps import StreamService, get_stream_service
from app.models.stream_models import (
    StreamStartRequest,
    StreamStartResponse,
    StreamStopRequest,
    StreamStopResponse,
)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.post("/start", response_model=StreamStartResponse)
def start_stream(
    request: StreamStartRequest,
    stream_service: StreamService = Depends(get_stream_service),
) -> StreamStartResponse:
    """
    Start RTSP stream processing with BAFS scheduling.

    Args:
        request: Stream start request
        stream_service: Stream service (injected)

    Returns:
        StreamStartResponse with start status
    """
    result = stream_service.start_stream(
        camera_id=request.camera_id,
        rtsp_url=request.rtsp_url,
        config_name=request.config_name,
    )

    return StreamStartResponse(
        camera_id=result.camera_id, started=result.success, message=result.message
    )


@router.post("/stop", response_model=StreamStopResponse)
def stop_stream(
    request: StreamStopRequest,
    stream_service: StreamService = Depends(get_stream_service),
) -> StreamStopResponse:
    """
    Stop RTSP stream processing.

    Args:
        request: Stream stop request
        stream_service: Stream service (injected)

    Returns:
        StreamStopResponse with stop status
    """
    result = stream_service.stop_stream(camera_id=request.camera_id)

    return StreamStopResponse(camera_id=result.camera_id, stopped=result.success)
