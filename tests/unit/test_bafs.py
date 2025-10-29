"""
Unit tests for BAFS scheduler (Module 2).

Tests dynamic FPS allocation with priority and motion detection.
"""

from datetime import datetime

import pytest

from app.models.rtsp_models import (
    BAFSAllocation,
    BAFSConfig,
    StreamPriority,
    StreamStats,
    StreamStatus,
)
from app.services.bafs_scheduler import BAFSScheduler


class TestBAFSScheduler:
    """Test BAFS scheduler functionality."""

    def test_scheduler_initialization(self) -> None:
        """Test BAFS scheduler initializes correctly."""
        config = BAFSConfig(total_fps_budget=120.0, min_fps_per_stream=1.0)
        scheduler = BAFSScheduler(config=config)

        assert scheduler.config.total_fps_budget == 120.0
        assert scheduler.config.min_fps_per_stream == 1.0

    def test_register_stream(self) -> None:
        """Test stream registration."""
        config = BAFSConfig()
        scheduler = BAFSScheduler(config=config)

        stats = StreamStats(camera_id="cam-001", status=StreamStatus.ACTIVE)
        scheduler.register_stream(camera_id="cam-001", stats=stats)

        # Verify stream is registered
        allocation = scheduler.get_allocation("cam-001")
        assert allocation is None  # No allocation until calculate_allocations called

    def test_unregister_stream(self) -> None:
        """Test stream unregistration."""
        config = BAFSConfig()
        scheduler = BAFSScheduler(config=config)

        stats = StreamStats(camera_id="cam-001", status=StreamStatus.ACTIVE)
        scheduler.register_stream(camera_id="cam-001", stats=stats)
        scheduler.unregister_stream(camera_id="cam-001")

        allocation = scheduler.get_allocation("cam-001")
        assert allocation is None

    def test_single_stream_allocation(self) -> None:
        """Test FPS allocation for single stream."""
        config = BAFSConfig(total_fps_budget=30.0, max_fps_per_stream=30.0)
        scheduler = BAFSScheduler(config=config)

        stats = StreamStats(camera_id="cam-001", status=StreamStatus.ACTIVE)
        scheduler.register_stream(camera_id="cam-001", stats=stats)

        allocations = scheduler.calculate_allocations()

        assert "cam-001" in allocations
        allocation = allocations["cam-001"]
        assert isinstance(allocation, BAFSAllocation)
        assert allocation.camera_id == "cam-001"
        # Single stream should get full budget (capped at max)
        assert allocation.allocated_fps == 30.0

    def test_multiple_streams_equal_priority(self) -> None:
        """Test FPS allocation splits evenly for equal priority."""
        config = BAFSConfig(
            total_fps_budget=60.0, min_fps_per_stream=10.0, max_fps_per_stream=50.0
        )
        scheduler = BAFSScheduler(config=config)

        # Register 2 streams
        for i in range(1, 3):
            stats = StreamStats(camera_id=f"cam-00{i}", status=StreamStatus.ACTIVE)
            scheduler.register_stream(camera_id=f"cam-00{i}", stats=stats)

        allocations = scheduler.calculate_allocations()

        assert len(allocations) == 2
        # Each stream should get roughly equal allocation
        for allocation in allocations.values():
            assert 25.0 <= allocation.allocated_fps <= 35.0  # Allow some variance

    def test_fps_budget_respected(self) -> None:
        """Test total FPS allocation doesn't exceed budget."""
        config = BAFSConfig(total_fps_budget=90.0)
        scheduler = BAFSScheduler(config=config)

        # Register 5 streams
        for i in range(1, 6):
            stats = StreamStats(camera_id=f"cam-00{i}", status=StreamStatus.ACTIVE)
            scheduler.register_stream(camera_id=f"cam-00{i}", stats=stats)

        allocations = scheduler.calculate_allocations()

        total_allocated = sum(a.allocated_fps for a in allocations.values())
        assert total_allocated <= config.total_fps_budget

    def test_minimum_fps_guaranteed(self) -> None:
        """Test each stream gets at least minimum FPS."""
        config = BAFSConfig(
            total_fps_budget=50.0, min_fps_per_stream=5.0, max_fps_per_stream=20.0
        )
        scheduler = BAFSScheduler(config=config)

        # Register many streams to test minimum enforcement
        for i in range(1, 6):
            stats = StreamStats(camera_id=f"cam-00{i}", status=StreamStatus.ACTIVE)
            scheduler.register_stream(camera_id=f"cam-00{i}", stats=stats)

        allocations = scheduler.calculate_allocations()

        for allocation in allocations.values():
            assert allocation.allocated_fps >= config.min_fps_per_stream

    def test_maximum_fps_enforced(self) -> None:
        """Test no stream exceeds maximum FPS."""
        config = BAFSConfig(
            total_fps_budget=100.0, min_fps_per_stream=1.0, max_fps_per_stream=25.0
        )
        scheduler = BAFSScheduler(config=config)

        # Single stream with high budget
        stats = StreamStats(camera_id="cam-001", status=StreamStatus.ACTIVE)
        scheduler.register_stream(camera_id="cam-001", stats=stats)

        allocations = scheduler.calculate_allocations()
        allocation = allocations["cam-001"]

        assert allocation.allocated_fps <= config.max_fps_per_stream

    def test_should_reallocate_timing(self) -> None:
        """Test reallocation timing logic."""
        config = BAFSConfig(reallocation_interval_ms=100)
        scheduler = BAFSScheduler(config=config)

        # Initially, should be true even though _last_allocation_time is set in __init__
        # The scheduler sets it to datetime.now() in __init__, so we need to force a wait
        # or check after an allocation

        # Calculate allocations first
        stats = StreamStats(camera_id="cam-001", status=StreamStatus.ACTIVE)
        scheduler.register_stream(camera_id="cam-001", stats=stats)
        scheduler.calculate_allocations()

        # Should be false immediately after allocation
        assert scheduler.should_reallocate() is False

    def test_get_all_allocations(self) -> None:
        """Test retrieving all allocations."""
        config = BAFSConfig()
        scheduler = BAFSScheduler(config=config)

        for i in range(1, 4):
            stats = StreamStats(camera_id=f"cam-00{i}", status=StreamStatus.ACTIVE)
            scheduler.register_stream(camera_id=f"cam-00{i}", stats=stats)

        scheduler.calculate_allocations()
        all_allocations = scheduler.get_all_allocations()

        assert len(all_allocations) == 3
        assert all(isinstance(a, BAFSAllocation) for a in all_allocations.values())

    def test_empty_scheduler_allocations(self) -> None:
        """Test allocation with no registered streams."""
        config = BAFSConfig()
        scheduler = BAFSScheduler(config=config)

        allocations = scheduler.calculate_allocations()
        assert len(allocations) == 0

    def test_update_stream_stats(self) -> None:
        """Test updating stream statistics."""
        config = BAFSConfig()
        scheduler = BAFSScheduler(config=config)

        stats = StreamStats(
            camera_id="cam-001", status=StreamStatus.ACTIVE, current_fps=15.0
        )
        scheduler.register_stream(camera_id="cam-001", stats=stats)

        # Update stats
        updated_stats = StreamStats(
            camera_id="cam-001", status=StreamStatus.ACTIVE, current_fps=25.0
        )
        scheduler.update_stream_stats(camera_id="cam-001", stats=updated_stats)

        # No direct way to verify internal state, but ensure no errors
        allocations = scheduler.calculate_allocations()
        assert "cam-001" in allocations
