"""
Stream management service with RTSP and BAFS integration (Module 2).

Manages RTSP stream capture with Budget-Aware Frame Scheduling.
"""

import asyncio
import logging
import socket
from collections.abc import AsyncGenerator, Mapping
from typing import Any

import cv2
import numpy as np

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

    async def generate_mjpeg_stream(self, camera_id: str) -> AsyncGenerator[bytes, None]:
        """
        Generate MJPEG stream from camera frames.

        Args:
            camera_id: Camera identifier

        Yields:
            MJPEG frame bytes
        """
        frame_queue = self._queue_manager.get_queue(camera_id)
        if frame_queue is None:
            logger.error("Frame queue not found for camera %s", camera_id)
            return

        logger.info("Starting MJPEG stream for camera %s", camera_id)

        try:
            while True:
                # Get latest frame from queue
                frame = frame_queue.peek_latest()

                if frame is not None:
                    # Encode frame as JPEG
                    try:
                        _, buffer = cv2.imencode(".jpg", frame.data)
                        frame_bytes = buffer.tobytes()

                        # Yield MJPEG frame
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                        )
                    except Exception as e:
                        logger.exception("Error encoding frame: %s", e)

                # Small delay to control frame rate
                await asyncio.sleep(0.033)  # ~30 FPS

        except asyncio.CancelledError:
            logger.info("MJPEG stream cancelled for camera %s", camera_id)
        except Exception as e:
            logger.exception("Error in MJPEG stream for camera %s: %s", camera_id, e)

    async def discover_rtsp_cameras(
        self, network: str = "192.168.1.0/24", timeout: float = 2.0
    ) -> list[dict[str, str]]:
        """
        Auto-discover RTSP cameras on the network.

        Scans common RTSP ports and tests common URL patterns.

        Args:
            network: Network to scan in CIDR notation (default: 192.168.1.0/24)
            timeout: Connection timeout in seconds

        Returns:
            List of discovered camera information dictionaries
        """
        discovered_cameras: list[dict[str, str]] = []

        # Common RTSP ports
        rtsp_ports = [554, 8554, 5554]

        # Common RTSP URL patterns for different manufacturers
        url_patterns = [
            "/stream",
            "/stream1",
            "/live",
            "/live/main",
            "/cam/realmonitor",
            "/h264",
            "/h264_stream",
            "/video.h264",
            "/Streaming/Channels/101",  # Hikvision
            "/axis-media/media.amp",  # Axis
            "/onvif1",  # ONVIF
            "/ch0_0.h264",  # Dahua
        ]

        logger.info("Starting RTSP camera discovery on network %s", network)

        # Parse network range
        base_ip = network.split("/")[0].rsplit(".", 1)[0]
        start_ip = 1
        end_ip = 255

        # Scan IP range
        for last_octet in range(start_ip, min(end_ip, 20)):  # Limit scan to first 20 IPs
            ip = f"{base_ip}.{last_octet}"

            for port in rtsp_ports:
                # Check if port is open
                if await self._is_port_open(ip, port, timeout):
                    logger.info("Found open RTSP port at %s:%d", ip, port)

                    # Try different URL patterns
                    for pattern in url_patterns:
                        rtsp_url = f"rtsp://{ip}:{port}{pattern}"

                        # Try to connect
                        if await self._test_rtsp_url(rtsp_url, timeout):
                            discovered_cameras.append(
                                {
                                    "ip": ip,
                                    "port": str(port),
                                    "rtsp_url": rtsp_url,
                                    "status": "accessible",
                                }
                            )
                            logger.info("Discovered RTSP camera: %s", rtsp_url)
                            break  # Found working URL for this IP

        logger.info("Discovery complete. Found %d cameras", len(discovered_cameras))
        return discovered_cameras

    async def discover_camera_for_stream(
        self, camera_id: str, network: str = "192.168.1.0/24", timeout: float = 2.0
    ) -> str | None:
        """
        Discover a single RTSP camera for immediate stream start.

        Useful for auto-discovery mode in stream start.

        Args:
            camera_id: Camera identifier (for logging)
            network: Network to scan
            timeout: Connection timeout

        Returns:
            First discovered RTSP URL or None if no camera found
        """
        logger.info("Auto-discovering camera for %s on network %s", camera_id, network)

        discovered = await self.discover_rtsp_cameras(network=network, timeout=timeout)

        if not discovered:
            logger.warning("No cameras discovered for %s", camera_id)
            return None

        # Return first discovered camera
        rtsp_url = discovered[0]["rtsp_url"]
        logger.info("Auto-discovered URL for %s: %s", camera_id, rtsp_url)
        return rtsp_url

    async def _is_port_open(self, ip: str, port: int, timeout: float) -> bool:
        """
        Check if a port is open on an IP address.

        Args:
            ip: IP address
            port: Port number
            timeout: Connection timeout

        Returns:
            True if port is open
        """
        try:
            # Use asyncio to avoid blocking
            future = asyncio.open_connection(ip, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False

    async def _test_rtsp_url(self, rtsp_url: str, timeout: float) -> bool:
        """
        Test if an RTSP URL is accessible.

        Args:
            rtsp_url: RTSP URL to test
            timeout: Connection timeout

        Returns:
            True if URL is accessible
        """
        try:
            # Use asyncio to run OpenCV test in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._test_rtsp_url_sync, rtsp_url, timeout
            )
            return result
        except Exception as e:
            logger.debug("Failed to test RTSP URL %s: %s", rtsp_url, e)
            return False

    def _test_rtsp_url_sync(self, rtsp_url: str, timeout: float) -> bool:
        """
        Synchronous RTSP URL test using OpenCV.

        Args:
            rtsp_url: RTSP URL to test
            timeout: Connection timeout

        Returns:
            True if URL is accessible
        """
        try:
            cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout * 1000))

            if cap.isOpened():
                # Try to read one frame
                ret, _ = cap.read()
                cap.release()
                return ret
            return False
        except Exception:
            return False


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
