"""
Stream management service with RTSP and BAFS integration (Module 2).

Manages RTSP stream capture with Budget-Aware Frame Scheduling.
"""

import logging
from collections.abc import Mapping

from app.models.rtsp_models import (
    RTSPConfig,
    StreamControlResponse,
    StreamPriority,
    StreamStats,
    StreamStatus,
)
from app.services.bafs_scheduler import get_bafs_scheduler
from app.services.frame_queue import get_frame_queue_manager
from app.services.rtsp_client import get_rtsp_client_manager

logger = logging.getLogger(__name__)


class StreamService:
    """Stream management service with RTSP and BAFS."""

    def __init__(self) -> None:
        """Initialize stream service."""
        self._rtsp_manager = get_rtsp_client_manager()
        self._queue_manager = get_frame_queue_manager()
        self._bafs_scheduler = get_bafs_scheduler()
        logger.info("Stream service initialized with RTSP and BAFS support")

    def start_stream(
        self,
        camera_id: str,
        rtsp_url: str,
        config_name: str,
        priority: StreamPriority = StreamPriority.MEDIUM,
        buffer_size: int = 10,
    ) -> StreamControlResponse:
        """
        Start RTSP stream processing with BAFS scheduling.

        Args:
            camera_id: Unique camera identifier
            rtsp_url: RTSP stream URL
            config_name: Configuration profile name (reserved for future use)
            priority: Stream priority for BAFS allocation
            buffer_size: Frame buffer size

        Returns:
            Stream control response
        """
        try:
            # Check if stream already exists
            if self._rtsp_manager.get_client(camera_id) is not None:
                return StreamControlResponse(
                    success=False,
                    camera_id=camera_id,
                    message=f"Stream {camera_id} is already running",
                    current_status=StreamStatus.ACTIVE,
                )

            # Create RTSP configuration
            rtsp_config = RTSPConfig(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                priority=priority,
                buffer_size=buffer_size,
            )

            # Create frame queue
            frame_queue = self._queue_manager.create_queue(
                camera_id=camera_id, max_size=buffer_size
            )

            # Create RTSP client
            rtsp_client = self._rtsp_manager.create_client(
                config=rtsp_config, frame_queue=frame_queue
            )

            # Register with BAFS scheduler
            stats = rtsp_client.get_stats()
            self._bafs_scheduler.register_stream(camera_id=camera_id, stats=stats)

            # Start capture
            if not rtsp_client.start():
                # Cleanup on failure
                self._cleanup_stream(camera_id)
                return StreamControlResponse(
                    success=False,
                    camera_id=camera_id,
                    message=f"Failed to start RTSP capture for {camera_id}",
                    current_status=StreamStatus.FAILED,
                )

            logger.info("Started RTSP stream for camera %s", camera_id)

            return StreamControlResponse(
                success=True,
                camera_id=camera_id,
                message=f"Stream {camera_id} started successfully with BAFS scheduling",
                current_status=StreamStatus.ACTIVE,
            )

        except Exception as e:
            logger.exception("Error starting stream %s: %s", camera_id, e)
            self._cleanup_stream(camera_id)
            return StreamControlResponse(
                success=False,
                camera_id=camera_id,
                message=f"Error starting stream: {e}",
                current_status=StreamStatus.FAILED,
            )

    def stop_stream(self, camera_id: str) -> StreamControlResponse:
        """
        Stop RTSP stream processing.

        Args:
            camera_id: Unique camera identifier

        Returns:
            Stream control response
        """
        try:
            client = self._rtsp_manager.get_client(camera_id)
            if client is None:
                return StreamControlResponse(
                    success=False,
                    camera_id=camera_id,
                    message=f"Stream {camera_id} not found",
                    current_status=StreamStatus.IDLE,
                )

            # Stop RTSP client
            client.stop()

            # Cleanup resources
            self._cleanup_stream(camera_id)

            logger.info("Stopped RTSP stream for camera %s", camera_id)

            return StreamControlResponse(
                success=True,
                camera_id=camera_id,
                message=f"Stream {camera_id} stopped successfully",
                current_status=StreamStatus.STOPPED,
            )

        except Exception as e:
            logger.exception("Error stopping stream %s: %s", camera_id, e)
            return StreamControlResponse(
                success=False,
                camera_id=camera_id,
                message=f"Error stopping stream: {e}",
                current_status=StreamStatus.FAILED,
            )

    def get_stream_stats(self, camera_id: str) -> StreamStats | None:
        """
        Get statistics for a stream.

        Args:
            camera_id: Camera identifier

        Returns:
            Stream statistics or None if not found
        """
        client = self._rtsp_manager.get_client(camera_id)
        if client is None:
            return None
        return client.get_stats()

    def get_all_stream_stats(self) -> Mapping[str, StreamStats]:
        """
        Get statistics for all active streams.

        Returns:
            Dictionary mapping camera_id to StreamStats
        """
        stats: dict[str, StreamStats] = {}
        for camera_id in self._rtsp_manager.get_all_camera_ids():
            stream_stats = self.get_stream_stats(camera_id)
            if stream_stats is not None:
                stats[camera_id] = stream_stats
        return stats

    def _cleanup_stream(self, camera_id: str) -> None:
        """
        Clean up resources for a stream.

        Args:
            camera_id: Camera identifier
        """
        # Unregister from BAFS
        self._bafs_scheduler.unregister_stream(camera_id)

        # Remove frame queue
        self._queue_manager.remove_queue(camera_id)

        # Remove RTSP client
        self._rtsp_manager.remove_client(camera_id)


# Global stream service instance
_stream_service_instance: StreamService | None = None


def get_stream_service() -> StreamService:
    """
    Dependency injection for stream service.

    Returns:
        StreamService instance
    """
    global _stream_service_instance
    if _stream_service_instance is None:
        _stream_service_instance = StreamService()
    return _stream_service_instance
