"""
Pydantic v2 Configuration Models with Strict Typing.

All config models use strict=True to enforce type safety.
"""

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    """Application configuration from environment variables."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=(),  # Allow model_* field names
    )

    # Application
    app_env: str = Field(default="development", description="Environment: development/production")
    app_name: str = Field(default="smart-attendance", description="Application name")
    log_level: str = Field(default="info", description="Logging level")

    # Server
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")
    server_workers: int = Field(default=1, description="Number of workers")

    # Device
    device_id: str = Field(default="edge-device-001", description="Unique device identifier")
    device_model: str = Field(default="jetson-nano", description="Device model")
    device_location: str = Field(default="lab-entrance", description="Device physical location")

    # MLflow
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000", description="MLflow tracking server URI"
    )
    mlflow_experiment_name: str = Field(
        default="smart-attendance", description="MLflow experiment name"
    )
    mlflow_artifact_root: str = Field(default="./mlruns", description="Artifact storage path")

    # Model Store
    model_store_path: str = Field(default="./models", description="Local model storage path")
    model_download_retry: int = Field(default=3, description="Model download retry attempts")
    model_download_timeout: int = Field(default=300, description="Model download timeout (s)")

    # Database
    db_path: str = Field(default="./data/attendance.db", description="SQLite database path")
    db_encryption_key: str = Field(
        default="change-me", description="Database encryption key (32 bytes)"
    )

    # RTSP
    rtsp_buffer_size: int = Field(default=100, description="Frame buffer size")
    rtsp_reconnect_delay: int = Field(default=5, description="Reconnect delay (s)")
    rtsp_max_reconnect: int = Field(default=10, description="Max reconnect attempts")

    # BAFS Scheduler
    bafs_motion_threshold: float = Field(
        default=0.3, description="Motion threshold for keyframe selection"
    )
    bafs_yaw_threshold: float = Field(
        default=20.0, description="Yaw angle threshold (degrees)"
    )
    bafs_keyframe_interval: int = Field(default=30, description="Max frames between keyframes")

    # Detection
    detector_confidence_threshold: float = Field(
        default=0.5, description="Detection confidence threshold"
    )
    detector_nms_threshold: float = Field(default=0.45, description="NMS IoU threshold")

    # Recognition
    recognition_threshold: float = Field(
        default=0.7, description="Recognition confidence threshold"
    )
    embedding_dim: int = Field(default=512, description="Embedding dimension")

    # Attendance
    attendance_min_confidence: float = Field(
        default=0.75, description="Minimum confidence for attendance"
    )
    attendance_debounce_seconds: int = Field(
        default=300, description="Debounce time between records (s)"
    )

    # Security
    jwt_secret_key: str = Field(default="change-me", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expire_minutes: int = Field(default=60, description="JWT expiration time")

    # Cloud Sync
    cloud_endpoint: str = Field(
        default="https://api.example.com", description="Cloud API endpoint"
    )
    cloud_sync_interval: int = Field(default=3600, description="Sync interval (s)")
    cloud_tls_cert: str = Field(default="./certs/client.crt", description="Client TLS cert")
    cloud_tls_key: str = Field(default="./certs/client.key", description="Client TLS key")


# Global config singleton
_config_instance: AppConfig | None = None


def get_config() -> AppConfig:
    """Get or create global config singleton.

    Returns:
        AppConfig: Application configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance
