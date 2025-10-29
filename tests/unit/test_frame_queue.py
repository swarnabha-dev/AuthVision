"""
Unit tests for frame queue (Module 2).

Tests thread-safe frame buffering with overflow handling.
"""

import numpy as np
import pytest

from app.models.rtsp_models import Frame, FrameMetadata
from app.services.frame_queue import FrameQueue, FrameQueueManager
from datetime import datetime


class TestFrameQueue:
    """Test frame queue functionality."""

    def create_test_frame(self, camera_id: str, frame_id: int) -> Frame:
        """Create a test frame."""
        metadata = FrameMetadata(
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=datetime.now(),
            width=640,
            height=480,
            channels=3,
            fps=30.0,
        )
        data = np.zeros((480, 640, 3), dtype=np.uint8)
        return Frame(metadata=metadata, data=data)

    def test_queue_initialization(self) -> None:
        """Test queue initializes correctly."""
        queue = FrameQueue(camera_id="cam-001", max_size=10)

        assert queue.camera_id == "cam-001"
        assert queue.max_size == 10
        assert queue.is_empty() is True
        assert queue.size() == 0

    def test_put_and_get_frame(self) -> None:
        """Test adding and retrieving frames."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        frame = self.create_test_frame("cam-001", 0)
        result = queue.put(frame)

        assert result is True
        assert queue.size() == 1
        assert queue.is_empty() is False

        retrieved = queue.get()
        assert retrieved is not None
        assert retrieved.metadata.frame_id == 0
        assert queue.is_empty() is True

    def test_fifo_ordering(self) -> None:
        """Test frames are retrieved in FIFO order."""
        queue = FrameQueue(camera_id="cam-001", max_size=10)

        # Add 3 frames
        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        # Retrieve should be in order
        for i in range(3):
            frame = queue.get()
            assert frame is not None
            assert frame.metadata.frame_id == i

    def test_overflow_drops_oldest(self) -> None:
        """Test overflow drops oldest frame."""
        queue = FrameQueue(camera_id="cam-001", max_size=3)

        # Fill queue
        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        assert queue.is_full() is True

        # Add one more (should drop frame 0)
        frame = self.create_test_frame("cam-001", 3)
        result = queue.put(frame)

        assert result is False  # Indicates overflow
        assert queue.get_dropped_count() == 1

        # First frame should now be frame 1 (frame 0 was dropped)
        first = queue.get()
        assert first is not None
        assert first.metadata.frame_id == 1

    def test_peek_does_not_remove(self) -> None:
        """Test peek returns frame without removing it."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        frame = self.create_test_frame("cam-001", 42)
        queue.put(frame)

        peeked = queue.peek()
        assert peeked is not None
        assert peeked.metadata.frame_id == 42
        assert queue.size() == 1  # Still in queue

        # Can still get the frame
        retrieved = queue.get()
        assert retrieved is not None
        assert retrieved.metadata.frame_id == 42

    def test_get_latest_frame(self) -> None:
        """Test getting most recent frame."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        latest = queue.get_latest()
        assert latest is not None
        assert latest.metadata.frame_id == 2  # Most recent

    def test_peek_latest_frame(self) -> None:
        """Test peeking at most recent frame."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        latest = queue.peek_latest()
        assert latest is not None
        assert latest.metadata.frame_id == 2
        assert queue.size() == 3  # Not removed

    def test_clear_queue(self) -> None:
        """Test clearing all frames."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        count = queue.clear()
        assert count == 3
        assert queue.is_empty() is True

    def test_get_all_frames(self) -> None:
        """Test getting all frames at once."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        for i in range(3):
            frame = self.create_test_frame("cam-001", i)
            queue.put(frame)

        all_frames = queue.get_all()
        assert len(all_frames) == 3
        assert all_frames[0].metadata.frame_id == 0
        assert all_frames[2].metadata.frame_id == 2
        assert queue.is_empty() is True  # Cleared

    def test_empty_queue_operations(self) -> None:
        """Test operations on empty queue."""
        queue = FrameQueue(camera_id="cam-001", max_size=5)

        assert queue.get() is None
        assert queue.peek() is None
        assert queue.get_latest() is None
        assert queue.peek_latest() is None
        assert queue.get_all() == []


class TestFrameQueueManager:
    """Test frame queue manager functionality."""

    def test_manager_initialization(self) -> None:
        """Test manager initializes correctly."""
        manager = FrameQueueManager()
        assert manager.get_all_camera_ids() == []

    def test_create_queue(self) -> None:
        """Test creating a queue."""
        manager = FrameQueueManager()

        queue = manager.create_queue(camera_id="cam-001", max_size=10)
        assert queue.camera_id == "cam-001"
        assert queue.max_size == 10

    def test_create_duplicate_queue_raises(self) -> None:
        """Test creating duplicate queue raises ValueError."""
        manager = FrameQueueManager()

        manager.create_queue(camera_id="cam-001", max_size=10)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_queue(camera_id="cam-001", max_size=10)

    def test_get_queue(self) -> None:
        """Test retrieving a queue."""
        manager = FrameQueueManager()

        created = manager.create_queue(camera_id="cam-001", max_size=10)
        retrieved = manager.get_queue(camera_id="cam-001")

        assert retrieved is created

    def test_get_nonexistent_queue(self) -> None:
        """Test getting non-existent queue returns None."""
        manager = FrameQueueManager()

        queue = manager.get_queue(camera_id="cam-999")
        assert queue is None

    def test_remove_queue(self) -> None:
        """Test removing a queue."""
        manager = FrameQueueManager()

        manager.create_queue(camera_id="cam-001", max_size=10)
        result = manager.remove_queue(camera_id="cam-001")

        assert result is True
        assert manager.get_queue(camera_id="cam-001") is None

    def test_remove_nonexistent_queue(self) -> None:
        """Test removing non-existent queue returns False."""
        manager = FrameQueueManager()

        result = manager.remove_queue(camera_id="cam-999")
        assert result is False

    def test_get_all_camera_ids(self) -> None:
        """Test getting all camera IDs."""
        manager = FrameQueueManager()

        manager.create_queue(camera_id="cam-001", max_size=10)
        manager.create_queue(camera_id="cam-002", max_size=10)

        camera_ids = manager.get_all_camera_ids()
        assert len(camera_ids) == 2
        assert "cam-001" in camera_ids
        assert "cam-002" in camera_ids

    def test_clear_all_queues(self) -> None:
        """Test clearing all queues."""
        manager = FrameQueueManager()

        queue1 = manager.create_queue(camera_id="cam-001", max_size=5)
        queue2 = manager.create_queue(camera_id="cam-002", max_size=5)

        # Add frames
        metadata = FrameMetadata(
            camera_id="cam-001",
            frame_id=0,
            timestamp=datetime.now(),
            width=640,
            height=480,
            channels=3,
            fps=30.0,
        )
        data = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = Frame(metadata=metadata, data=data)

        queue1.put(frame)
        queue2.put(frame)

        manager.clear_all()

        assert queue1.is_empty() is True
        assert queue2.is_empty() is True
