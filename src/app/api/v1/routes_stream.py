"""
Stream management routes (Module 2: RTSP + BAFS integration).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.deps import StreamService, get_stream_service
from app.models.stream_models import (
    AutoDiscoverRequest,
    AutoDiscoverResponse,
    StreamStartRequest,
    StreamStartResponse,
    StreamStopRequest,
    StreamStopResponse,
)

router = APIRouter(prefix="/stream", tags=["stream"])


@router.post("/start", response_model=StreamStartResponse)
async def start_stream(
    request: StreamStartRequest,
    stream_service: StreamService = Depends(get_stream_service),
) -> StreamStartResponse:
    """
    Start RTSP stream processing with BAFS scheduling.

    Supports two modes:
    1. Manual mode: Provide rtsp_url directly
    2. Auto-discovery mode: Set auto_discover=true, optionally specify discovery_network

    Args:
        request: Stream start request with optional auto-discovery
        stream_service: Stream service (injected)

    Returns:
        StreamStartResponse with start status and discovered URL

    Raises:
        HTTPException: If auto-discovery fails or required parameters missing
    """
    # Mode 1: Auto-discovery
    if request.auto_discover:
        discovered_url = await stream_service.discover_camera_for_stream(
            camera_id=request.camera_id,
            network=request.discovery_network,
        )

        if discovered_url is None:
            raise HTTPException(
                status_code=404,
                detail=f"Could not auto-discover camera for {request.camera_id}",
            )

        # Use discovered URL
        rtsp_url = discovered_url
        discovered = True

    # Mode 2: Manual URL
    else:
        if request.rtsp_url is None:
            raise HTTPException(
                status_code=400,
                detail="Either rtsp_url must be provided or auto_discover must be true",
            )
        rtsp_url = request.rtsp_url
        discovered = False

    # Map priority string to enum
    from app.models.rtsp_models import StreamPriority

    priority_map = {
        "low": StreamPriority.LOW,
        "medium": StreamPriority.MEDIUM,
        "high": StreamPriority.HIGH,
        "critical": StreamPriority.CRITICAL,
    }
    priority = priority_map.get(request.priority.lower(), StreamPriority.MEDIUM)

    # Start the stream
    result = stream_service.start_stream(
        camera_id=request.camera_id,
        rtsp_url=rtsp_url,
        config_name=request.config_name,
        priority=priority,
    )

    return StreamStartResponse(
        camera_id=result.camera_id,
        started=result.success,
        message=result.message,
        rtsp_url=rtsp_url if result.success else None,
        discovered=discovered,
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


@router.get("/video/{camera_id}")
async def stream_video(
    camera_id: str,
    stream_service: StreamService = Depends(get_stream_service),
) -> StreamingResponse:
    """
    Stream live video from camera as MJPEG.

    View in browser: http://localhost:8000/api/v1/stream/video/cam-001
    Or embed in HTML: <img src="http://localhost:8000/api/v1/stream/video/cam-001">

    Args:
        camera_id: Camera identifier
        stream_service: Stream service (injected)

    Returns:
        MJPEG video stream

    Raises:
        HTTPException: If camera not found or not streaming
    """
    # Check if stream exists
    stats = stream_service.get_stream_stats(camera_id)
    if stats is None:
        raise HTTPException(
            status_code=404, detail=f"Camera {camera_id} not found or not streaming"
        )

    # Generate MJPEG stream
    return StreamingResponse(
        stream_service.generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/discover")
async def discover_streams(
    stream_service: StreamService = Depends(get_stream_service),
) -> dict[str, list[dict[str, str]]]:
    """
    Auto-discover RTSP cameras on the local network.

    Scans common RTSP ports and tests common URL patterns.
    This is the simple version for backward compatibility.

    Returns:
        Dictionary with discovered camera information
    """
    discovered = await stream_service.discover_rtsp_cameras()
    return {"cameras": discovered}


@router.post("/discover-auto", response_model=AutoDiscoverResponse)
async def discover_and_start(
    request: AutoDiscoverRequest,
    stream_service: StreamService = Depends(get_stream_service),
) -> AutoDiscoverResponse:
    """
    Auto-discover RTSP cameras and optionally start streams automatically.

    This endpoint provides full automation:
    1. Scans network for cameras
    2. Optionally starts streams for all discovered cameras
    3. Registers them with BAFS scheduler
    4. Returns list of started camera IDs

    Args:
        request: Auto-discovery configuration
        stream_service: Stream service (injected)

    Returns:
        Discovery results with optional auto-started camera IDs
    """
    # Discover cameras
    discovered = await stream_service.discover_rtsp_cameras(
        network=request.network,
        timeout=request.timeout,
    )

    # Limit to max_cameras
    discovered = discovered[: request.max_cameras]

    auto_started: list[str] = []

    # Auto-start if requested
    if request.auto_start and discovered:
        from app.models.rtsp_models import StreamPriority

        for idx, camera_info in enumerate(discovered):
            camera_id = f"auto-cam-{idx + 1:03d}"
            rtsp_url = camera_info["rtsp_url"]

            # Start stream
            result = stream_service.start_stream(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                config_name="default",
                priority=StreamPriority.MEDIUM,
            )

            if result.success:
                auto_started.append(camera_id)
                # Update camera info with assigned ID
                camera_info["camera_id"] = camera_id

    return AutoDiscoverResponse(
        cameras=discovered,
        total_found=len(discovered),
        auto_started=auto_started,
    )
