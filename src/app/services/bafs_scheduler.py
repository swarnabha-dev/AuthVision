"""
BAFS (Budget-Aware Frame Scheduler) service (Module 2).

Dynamic FPS allocation across multiple RTSP streams based on:
- Stream priority levels
- Motion detection status
- Total FPS budget constraints
"""

import logging
from collections.abc import Mapping
from datetime import datetime
from threading import Lock

from app.models.rtsp_models import (
    BAFSAllocation,
    BAFSConfig,
    StreamPriority,
    StreamStats,
)

logger = logging.getLogger(__name__)


class BAFSScheduler:
    """
    Budget-Aware Frame Scheduler.

    Allocates FPS budget across active streams based on priority and motion.
    Thread-safe for concurrent stream updates.
    """

    def __init__(self, config: BAFSConfig) -> None:
        """
        Initialize BAFS scheduler.

        Args:
            config: BAFS configuration with budget and priority weights
        """
        self.config = config
        self._lock = Lock()
        self._stream_stats: dict[str, StreamStats] = {}
        self._allocations: dict[str, BAFSAllocation] = {}
        self._last_allocation_time = datetime.now()

        logger.info(
            "BAFS scheduler initialized with budget=%.1f FPS",
            config.total_fps_budget,
        )

    def register_stream(self, camera_id: str, stats: StreamStats) -> None:
        """
        Register a new stream for FPS allocation.

        Args:
            camera_id: Unique camera identifier
            stats: Current stream statistics
        """
        with self._lock:
            self._stream_stats[camera_id] = stats
            logger.info("Registered stream %s for BAFS scheduling", camera_id)

    def unregister_stream(self, camera_id: str) -> None:
        """
        Remove a stream from FPS allocation.

        Args:
            camera_id: Camera identifier to remove
        """
        with self._lock:
            self._stream_stats.pop(camera_id, None)
            self._allocations.pop(camera_id, None)
            logger.info("Unregistered stream %s from BAFS scheduling", camera_id)

    def update_stream_stats(self, camera_id: str, stats: StreamStats) -> None:
        """
        Update statistics for an active stream.

        Args:
            camera_id: Camera identifier
            stats: Updated stream statistics
        """
        with self._lock:
            if camera_id in self._stream_stats:
                self._stream_stats[camera_id] = stats

    def calculate_allocations(self) -> Mapping[str, BAFSAllocation]:
        """
        Calculate FPS allocations for all active streams.

        Uses priority-based weighted allocation with motion detection boost.

        Returns:
            Dictionary mapping camera_id to BAFSAllocation
        """
        with self._lock:
            if not self._stream_stats:
                return {}

            # Calculate priority scores for each stream
            scores: dict[str, float] = {}
            for camera_id, stats in self._stream_stats.items():
                # Get priority weight from config
                priority_weight = self._get_priority_weight(stats)

                # Apply motion boost if enabled
                motion_multiplier = 1.0
                if (
                    self.config.motion_detection_enabled
                    and stats.current_fps > 0.0
                    and self._is_motion_detected(camera_id)
                ):
                    motion_multiplier = self.config.motion_fps_boost

                scores[camera_id] = priority_weight * motion_multiplier

            # Calculate total score
            total_score = sum(scores.values())
            if total_score == 0.0:
                # Equal allocation if all scores are zero
                total_score = float(len(scores))
                scores = {k: 1.0 for k in scores}

            # Allocate FPS proportionally
            allocations: dict[str, BAFSAllocation] = {}
            remaining_budget = self.config.total_fps_budget

            for camera_id, score in scores.items():
                # Calculate proportional allocation
                raw_fps = (score / total_score) * self.config.total_fps_budget

                # Clamp to min/max limits
                allocated_fps = max(
                    self.config.min_fps_per_stream,
                    min(raw_fps, self.config.max_fps_per_stream),
                )

                # Ensure we don't exceed remaining budget
                allocated_fps = min(allocated_fps, remaining_budget)
                remaining_budget -= allocated_fps

                stats = self._stream_stats[camera_id]
                allocations[camera_id] = BAFSAllocation(
                    camera_id=camera_id,
                    allocated_fps=allocated_fps,
                    priority=self._get_stream_priority(camera_id),
                    is_motion_active=self._is_motion_detected(camera_id),
                    allocation_timestamp=datetime.now(),
                )

                logger.debug(
                    "BAFS allocated %.1f FPS to camera %s (priority=%s, motion=%s)",
                    allocated_fps,
                    camera_id,
                    allocations[camera_id].priority,
                    allocations[camera_id].is_motion_active,
                )

            self._allocations = allocations
            self._last_allocation_time = datetime.now()

            return allocations

    def get_allocation(self, camera_id: str) -> BAFSAllocation | None:
        """
        Get current FPS allocation for a specific stream.

        Args:
            camera_id: Camera identifier

        Returns:
            Current allocation or None if stream not registered
        """
        with self._lock:
            return self._allocations.get(camera_id)

    def get_all_allocations(self) -> Mapping[str, BAFSAllocation]:
        """
        Get all current FPS allocations.

        Returns:
            Dictionary of all active allocations
        """
        with self._lock:
            return dict(self._allocations)

    def should_reallocate(self) -> bool:
        """
        Check if FPS reallocation should be triggered.

        Returns:
            True if reallocation interval has elapsed
        """
        elapsed_ms = (datetime.now() - self._last_allocation_time).total_seconds() * 1000
        return elapsed_ms >= self.config.reallocation_interval_ms

    def _get_priority_weight(self, stats: StreamStats) -> float:
        """Get priority weight for a stream from stats."""
        # This is a stub - actual priority should come from StreamStats
        # For now, return default MEDIUM priority weight
        return self.config.priority_weights[StreamPriority.MEDIUM]

    def _get_stream_priority(self, camera_id: str) -> StreamPriority:
        """Get stream priority (stub for now)."""
        return StreamPriority.MEDIUM

    def _is_motion_detected(self, camera_id: str) -> bool:
        """Check if motion is detected for a stream (stub for now)."""
        # This will be implemented when we add motion detection
        return False


# Global BAFS scheduler instance
_bafs_instance: BAFSScheduler | None = None


def get_bafs_scheduler() -> BAFSScheduler:
    """
    Get global BAFS scheduler instance.

    Returns:
        Global BAFS scheduler singleton

    Raises:
        RuntimeError: If scheduler not initialized
    """
    global _bafs_instance
    if _bafs_instance is None:
        # Initialize with default config
        _bafs_instance = BAFSScheduler(BAFSConfig())
    return _bafs_instance


def initialize_bafs_scheduler(config: BAFSConfig) -> None:
    """
    Initialize global BAFS scheduler with custom config.

    Args:
        config: BAFS configuration
    """
    global _bafs_instance
    _bafs_instance = BAFSScheduler(config)
    logger.info("Global BAFS scheduler initialized")
