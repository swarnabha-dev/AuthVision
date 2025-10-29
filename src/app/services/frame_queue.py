"""
Thread-safe frame queue manager (Module 2).

Manages frame buffering with overflow handling and thread-safe access.
"""

import logging
from collections import deque
from collections.abc import Sequence
from threading import Lock

from app.models.rtsp_models import Frame

logger = logging.getLogger(__name__)


class FrameQueue:
    """
    Thread-safe frame queue with overflow handling.

    Implements a bounded queue that drops oldest frames when full.
    """

    def __init__(self, camera_id: str, max_size: int = 10) -> None:
        """
        Initialize frame queue.

        Args:
            camera_id: Camera identifier for this queue
            max_size: Maximum number of frames to buffer
        """
        self.camera_id = camera_id
        self.max_size = max_size
        self._queue: deque[Frame] = deque(maxlen=max_size)
        self._lock = Lock()
        self._dropped_count = 0

        logger.info(
            "Frame queue created for camera %s (max_size=%d)", camera_id, max_size
        )

    def put(self, frame: Frame) -> bool:
        """
        Add a frame to the queue.

        If queue is full, oldest frame is dropped.

        Args:
            frame: Frame to add

        Returns:
            True if frame added successfully, False if frame was dropped
        """
        with self._lock:
            if len(self._queue) >= self.max_size:
                # Queue is full, drop oldest frame
                self._queue.popleft()
                self._dropped_count += 1
                logger.warning(
                    "Frame queue full for camera %s, dropped frame %d (total dropped: %d)",
                    self.camera_id,
                    frame.metadata.frame_id,
                    self._dropped_count,
                )
                return False

            self._queue.append(frame)
            return True

    def get(self) -> Frame | None:
        """
        Get and remove the oldest frame from queue.

        Returns:
            Oldest frame or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def peek(self) -> Frame | None:
        """
        Get the oldest frame without removing it.

        Returns:
            Oldest frame or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue[0]

    def get_latest(self) -> Frame | None:
        """
        Get and remove the most recent frame.

        Returns:
            Most recent frame or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue.pop()

    def peek_latest(self) -> Frame | None:
        """
        Get the most recent frame without removing it.

        Returns:
            Most recent frame or None if queue is empty
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue[-1]

    def clear(self) -> int:
        """
        Clear all frames from queue.

        Returns:
            Number of frames cleared
        """
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            logger.debug("Cleared %d frames from queue for camera %s", count, self.camera_id)
            return count

    def size(self) -> int:
        """
        Get current number of frames in queue.

        Returns:
            Current queue size
        """
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        """
        Check if queue is empty.

        Returns:
            True if queue has no frames
        """
        with self._lock:
            return len(self._queue) == 0

    def is_full(self) -> bool:
        """
        Check if queue is at maximum capacity.

        Returns:
            True if queue is full
        """
        with self._lock:
            return len(self._queue) >= self.max_size

    def get_dropped_count(self) -> int:
        """
        Get total number of dropped frames.

        Returns:
            Total frames dropped due to overflow
        """
        with self._lock:
            return self._dropped_count

    def get_all(self) -> Sequence[Frame]:
        """
        Get all frames from queue (clears queue).

        Returns:
            List of all frames in queue (oldest to newest)
        """
        with self._lock:
            frames = list(self._queue)
            self._queue.clear()
            return frames


class FrameQueueManager:
    """
    Manages multiple frame queues for different cameras.

    Provides centralized access to all camera frame queues.
    """

    def __init__(self) -> None:
        """Initialize frame queue manager."""
        self._queues: dict[str, FrameQueue] = {}
        self._lock = Lock()
        logger.info("Frame queue manager initialized")

    def create_queue(self, camera_id: str, max_size: int = 10) -> FrameQueue:
        """
        Create a new frame queue for a camera.

        Args:
            camera_id: Camera identifier
            max_size: Maximum queue size

        Returns:
            Created frame queue

        Raises:
            ValueError: If queue already exists for camera_id
        """
        with self._lock:
            if camera_id in self._queues:
                msg = f"Frame queue already exists for camera {camera_id}"
                raise ValueError(msg)

            queue = FrameQueue(camera_id=camera_id, max_size=max_size)
            self._queues[camera_id] = queue
            logger.info("Created frame queue for camera %s", camera_id)
            return queue

    def get_queue(self, camera_id: str) -> FrameQueue | None:
        """
        Get frame queue for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            Frame queue or None if not found
        """
        with self._lock:
            return self._queues.get(camera_id)

    def remove_queue(self, camera_id: str) -> bool:
        """
        Remove frame queue for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            True if queue was removed, False if not found
        """
        with self._lock:
            if camera_id in self._queues:
                self._queues[camera_id].clear()
                del self._queues[camera_id]
                logger.info("Removed frame queue for camera %s", camera_id)
                return True
            return False

    def get_all_camera_ids(self) -> Sequence[str]:
        """
        Get list of all camera IDs with active queues.

        Returns:
            List of camera identifiers
        """
        with self._lock:
            return list(self._queues.keys())

    def clear_all(self) -> None:
        """Clear all frame queues."""
        with self._lock:
            for queue in self._queues.values():
                queue.clear()
            logger.info("Cleared all frame queues")


# Global frame queue manager instance
_queue_manager_instance: FrameQueueManager | None = None


def get_frame_queue_manager() -> FrameQueueManager:
    """
    Get global frame queue manager instance.

    Returns:
        Global frame queue manager singleton
    """
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = FrameQueueManager()
    return _queue_manager_instance
