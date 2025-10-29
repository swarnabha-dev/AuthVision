"""
Timing utilities for performance measurement.

TODO: Implement in Module 3+ for model inference timing.
"""

import time
from typing import Any, Callable


class Timer:
    """Context manager for timing code blocks (stub implementation)."""

    def __init__(self, name: str) -> None:
        """Initialize timer.

        Args:
            name: Timer name for logging
        """
        self.name = name
        self.start_time: float = 0.0
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        """Start timer."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop timer and log elapsed time."""
        self.elapsed = time.perf_counter() - self.start_time
        print(f"[{self.name}] Elapsed: {self.elapsed * 1000:.2f} ms")


def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to time function execution.

    Args:
        func: Function to time

    Returns:
        Wrapped function
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with Timer(func.__name__):
            return func(*args, **kwargs)

    return wrapper
