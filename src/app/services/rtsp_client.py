"""
RTSP client with auto-reconnection (Module 2).

Handles RTSP stream capture using OpenCV with automatic reconnection logic.
"""

import logging
import time
from datetime import datetime
from threading import Event, Lock, Thread

import cv2
import numpy as np

from app.models.rtsp_models import (
    Frame,
    FrameMetadata,
    RTSPConfig,
    StreamStats,
    StreamStatus,
)
from app.services.frame_queue import FrameQueue

logger = logging.getLogger(__name__)


class RTSPClient:
    """
    RTSP stream client with auto-reconnection.

    Captures frames from RTSP stream in a separate thread with automatic
    reconnection on failures.
    """

    def __init__(self, config: RTSPConfig, frame_queue: FrameQueue) -> None:
        """
        Initialize RTSP client.

        Args:
            config: RTSP configuration
            frame_queue: Frame queue for captured frames
        """
        self.config = config
        self.frame_queue = frame_queue

        self._capture: cv2.VideoCapture | None = None
        self._capture_thread: Thread | None = None
        self._stop_event = Event()
        self._lock = Lock()

        # Statistics
        self._stats = StreamStats(
            camera_id=config.camera_id,
            status=StreamStatus.IDLE,
        )
        self._frame_count = 0
        self._start_time: float | None = None
        self._last_frame_time: float | None = None
        self._reconnect_attempts = 0

        logger.info("RTSP client created for camera %s", config.camera_id)

    def start(self) -> bool:
        """
        Start RTSP stream capture.

        Returns:
            True if capture started successfully
        """
        with self._lock:
            if self._capture_thread is not None and self._capture_thread.is_alive():
                logger.warning(
                    "RTSP capture already running for camera %s", self.config.camera_id
                )
                return False

            self._stop_event.clear()
            self._start_time = time.time()
            self._stats.status = StreamStatus.CONNECTING

            # Start capture thread
            self._capture_thread = Thread(
                target=self._capture_loop,
                name=f"rtsp-{self.config.camera_id}",
                daemon=True,
            )
            self._capture_thread.start()

            logger.info("Started RTSP capture for camera %s", self.config.camera_id)
            return True

    def stop(self) -> None:
        """Stop RTSP stream capture."""
        with self._lock:
            if self._capture_thread is None:
                return

            self._stop_event.set()

        # Wait for thread to finish
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=5.0)

        self._release_capture()
        self._stats.status = StreamStatus.STOPPED

        logger.info("Stopped RTSP capture for camera %s", self.config.camera_id)

    def get_stats(self) -> StreamStats:
        """
        Get current stream statistics.

        Returns:
            Current stream statistics
        """
        with self._lock:
            # Update stats
            if self._start_time is not None:
                self._stats.uptime_seconds = time.time() - self._start_time

            self._stats.frames_captured = self._frame_count
            self._stats.frames_dropped = self.frame_queue.get_dropped_count()
            self._stats.reconnect_count = self._reconnect_attempts

            # Calculate FPS
            if self._frame_count > 0 and self._start_time is not None:
                elapsed = time.time() - self._start_time
                if elapsed > 0:
                    self._stats.current_fps = self._frame_count / elapsed

            return self._stats

    def _capture_loop(self) -> None:
        """Main capture loop (runs in separate thread)."""
        while not self._stop_event.is_set():
            try:
                # Connect to stream
                if not self._connect():
                    if not self._handle_reconnection():
                        break
                    continue

                # Capture frames
                self._stats.status = StreamStatus.ACTIVE
                while not self._stop_event.is_set():
                    if not self._capture_frame():
                        # Capture failed, reconnect
                        self._stats.status = StreamStatus.RECONNECTING
                        break

            except Exception as e:
                logger.exception(
                    "Unexpected error in RTSP capture loop for camera %s: %s",
                    self.config.camera_id,
                    e,
                )
                self._stats.error_message = str(e)
                self._stats.status = StreamStatus.FAILED

                if not self._handle_reconnection():
                    break

    def _connect(self) -> bool:
        """
        Connect to RTSP stream.

        Returns:
            True if connection successful
        """
        try:
            logger.info("Connecting to RTSP stream: %s", self.config.rtsp_url)

            # Create VideoCapture with timeout
            capture = cv2.VideoCapture(self.config.rtsp_url, cv2.CAP_FFMPEG)

            # Set transport protocol
            if self.config.transport.lower() == "tcp":
                capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, self.config.timeout_ms)

            # Set buffer size
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not capture.isOpened():
                logger.error(
                    "Failed to open RTSP stream for camera %s", self.config.camera_id
                )
                return False

            with self._lock:
                self._capture = capture
                self._reconnect_attempts = 0

            logger.info("Connected to RTSP stream for camera %s", self.config.camera_id)
            return True

        except Exception as e:
            logger.exception("Error connecting to RTSP stream: %s", e)
            self._stats.error_message = str(e)
            return False

    def _capture_frame(self) -> bool:
        """
        Capture a single frame.

        Returns:
            True if frame captured successfully
        """
        if self._capture is None:
            return False

        try:
            ret, frame_data = self._capture.read()
            if not ret or frame_data is None:
                logger.warning(
                    "Failed to read frame from camera %s", self.config.camera_id
                )
                return False

            # Create frame metadata
            current_time = datetime.now()
            height, width = frame_data.shape[:2]
            channels = frame_data.shape[2] if len(frame_data.shape) > 2 else 1

            metadata = FrameMetadata(
                camera_id=self.config.camera_id,
                frame_id=self._frame_count,
                timestamp=current_time,
                width=width,
                height=height,
                channels=channels,
                fps=self._stats.current_fps,
            )

            # Create frame
            frame = Frame(metadata=metadata, data=frame_data.astype(np.uint8))

            # Add to queue
            self.frame_queue.put(frame)

            # Update statistics
            with self._lock:
                self._frame_count += 1
                self._last_frame_time = time.time()
                self._stats.last_frame_time = current_time

            return True

        except Exception as e:
            logger.exception("Error capturing frame: %s", e)
            self._stats.error_message = str(e)
            return False

    def _handle_reconnection(self) -> bool:
        """
        Handle reconnection logic.

        Returns:
            True if should continue reconnecting, False if max attempts reached
        """
        self._reconnect_attempts += 1

        if self._reconnect_attempts > self.config.max_reconnect_attempts:
            logger.error(
                "Max reconnection attempts reached for camera %s",
                self.config.camera_id,
            )
            self._stats.status = StreamStatus.FAILED
            self._stats.error_message = "Max reconnection attempts exceeded"
            return False

        logger.info(
            "Reconnection attempt %d/%d for camera %s",
            self._reconnect_attempts,
            self.config.max_reconnect_attempts,
            self.config.camera_id,
        )

        # Release current capture
        self._release_capture()

        # Wait before reconnecting
        delay_seconds = self.config.reconnect_delay_ms / 1000.0
        self._stop_event.wait(timeout=delay_seconds)

        return not self._stop_event.is_set()

    def _release_capture(self) -> None:
        """Release OpenCV VideoCapture resource."""
        with self._lock:
            if self._capture is not None:
                try:
                    self._capture.release()
                except Exception as e:
                    logger.exception("Error releasing capture: %s", e)
                finally:
                    self._capture = None


class RTSPClientManager:
    """
    Manages multiple RTSP clients.

    Provides centralized control of all RTSP stream clients.
    """

    def __init__(self) -> None:
        """Initialize RTSP client manager."""
        self._clients: dict[str, RTSPClient] = {}
        self._lock = Lock()
        logger.info("RTSP client manager initialized")

    def create_client(
        self, config: RTSPConfig, frame_queue: FrameQueue
    ) -> RTSPClient:
        """
        Create a new RTSP client.

        Args:
            config: RTSP configuration
            frame_queue: Frame queue for captured frames

        Returns:
            Created RTSP client

        Raises:
            ValueError: If client already exists for camera_id
        """
        with self._lock:
            if config.camera_id in self._clients:
                msg = f"RTSP client already exists for camera {config.camera_id}"
                raise ValueError(msg)

            client = RTSPClient(config=config, frame_queue=frame_queue)
            self._clients[config.camera_id] = client
            logger.info("Created RTSP client for camera %s", config.camera_id)
            return client

    def get_client(self, camera_id: str) -> RTSPClient | None:
        """
        Get RTSP client for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            RTSP client or None if not found
        """
        with self._lock:
            return self._clients.get(camera_id)

    def remove_client(self, camera_id: str) -> bool:
        """
        Remove and stop RTSP client.

        Args:
            camera_id: Camera identifier

        Returns:
            True if client was removed, False if not found
        """
        with self._lock:
            client = self._clients.get(camera_id)
            if client is None:
                return False

            client.stop()
            del self._clients[camera_id]
            logger.info("Removed RTSP client for camera %s", camera_id)
            return True

    def get_all_camera_ids(self) -> list[str]:
        """
        Get list of all camera IDs with active clients.

        Returns:
            List of camera identifiers
        """
        with self._lock:
            return list(self._clients.keys())

    def stop_all(self) -> None:
        """Stop all RTSP clients."""
        with self._lock:
            for client in self._clients.values():
                client.stop()
            logger.info("Stopped all RTSP clients")


# Global RTSP client manager instance
_rtsp_manager_instance: RTSPClientManager | None = None


def get_rtsp_client_manager() -> RTSPClientManager:
    """
    Get global RTSP client manager instance.

    Returns:
        Global RTSP client manager singleton
    """
    global _rtsp_manager_instance
    if _rtsp_manager_instance is None:
        _rtsp_manager_instance = RTSPClientManager()
    return _rtsp_manager_instance
