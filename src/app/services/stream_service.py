"""
Service stub: Stream management.

TODO: Implement RTSP capture and BAFS scheduler in Module 2.
"""

from datetime import datetime


class StreamService:
    """Stream management service (stub implementation)."""

    def __init__(self) -> None:
        """Initialize stream service."""
        self._active_streams: dict[str, bool] = {}

    def start_stream(self, camera_id: str, rtsp_url: str, config_name: str) -> tuple[bool, str]:
        """Start RTSP stream processing.

        Args:
            camera_id: Unique camera identifier
            rtsp_url: RTSP stream URL
            config_name: Configuration profile name

        Returns:
            Tuple of (success: bool, message: str)
        """
        # TODO: Implement RTSP reader + BAFS scheduler
        # For now, return stub response
        self._active_streams[camera_id] = True
        return (
            True,
            f"Stream {camera_id} started (STUB - RTSP+BAFS not implemented)",
        )

    def stop_stream(self, camera_id: str) -> bool:
        """Stop RTSP stream processing.

        Args:
            camera_id: Unique camera identifier

        Returns:
            True if stopped successfully
        """
        # TODO: Implement stream cleanup
        if camera_id in self._active_streams:
            del self._active_streams[camera_id]
            return True
        return False


def get_stream_service() -> StreamService:
    """Dependency injection for stream service.

    Returns:
        StreamService instance
    """
    return StreamService()
