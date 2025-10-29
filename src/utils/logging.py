"""
Structured JSON logging configuration.

TODO: Expand in Module 2+ with model_version, device_id, camera_id context.
"""

import logging
import sys
from typing import Any


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logger.

    Args:
        name: Logger name
        level: Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    # TODO: Add JSON formatter with model_version, device_id, camera_id fields
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger


# Default application logger
app_logger = setup_logger("smart-attendance")


def log_inference(
    model_name: str,
    latency_ms: float,
    device_id: str,
    camera_id: str,
    **kwargs: Any,
) -> None:
    """Log inference event with structured data.

    Args:
        model_name: Model name
        latency_ms: Inference latency in milliseconds
        device_id: Device identifier
        camera_id: Camera identifier
        **kwargs: Additional context fields
    """
    # TODO: Format as structured JSON in Module 3+
    app_logger.info(
        f"Inference: model={model_name}, latency={latency_ms:.2f}ms, "
        f"device={device_id}, camera={camera_id}"
    )
