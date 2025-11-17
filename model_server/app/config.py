"""Model Server Configuration - Pydantic v2 Settings."""

from __future__ import annotations

from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelServerConfig(BaseSettings):
    """Model server configuration with strict validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        validate_assignment=True,
        protected_namespaces=(),  # Allow 'model_' prefix fields
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8001, ge=1, le=65535, description="Server port")
    workers: int = Field(default=2, ge=1, le=16, description="Number of workers")
    
    # JWT Authentication settings
    jwt_secret: str = Field(
        default="your-super-secret-jwt-key-change-in-production",
        description="JWT secret key for signing tokens"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440, description="Access token expiration (minutes)")
    refresh_token_expire_days: int = Field(default=30, ge=1, le=90, description="Refresh token expiration (days)")
    
    # Internal service token for backend ↔ model layer auth (deprecated - use JWT)
    internal_service_token: str = Field(
        default="change_me_in_production",
        description="Internal service authentication token (legacy)"
    )
    
    # DeepFace model settings (following the architecture spec)
    model_name: Literal["ArcFace", "Facenet", "Facenet512", "VGG-Face", "OpenFace", "DeepFace", "DeepID", "Dlib"] = Field(
        default="ArcFace",
        description="Recognition model (ArcFace for 512-D embeddings)"
    )
    detector_backend: Literal["opencv", "ssd", "dlib", "mtcnn", "retinaface", "mediapipe", "yolov8", "yunet", "fastmtcnn"] = Field(
        default="yolov8",
        description="Face detector backend (yolov8 for YOLOv8n)"
    )
    distance_metric: Literal["cosine", "euclidean", "euclidean_l2"] = Field(
        default="cosine",
        description="Distance metric for matching"
    )
    
    # Recognition settings
    recognition_threshold: float = Field(default=0.40, ge=0.0, le=1.0, description="Recognition threshold (cosine distance) - balanced for accuracy")
    detection_confidence_threshold: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum YOLO detection confidence (0.65 = 65% confidence)")
    align: bool = Field(default=True, description="Enable face alignment based on landmarks")
    anti_spoof_enabled: bool = Field(default=True, description="Enable anti-spoofing detection")
    normalization: Literal["base", "raw", "Facenet", "Facenet2018", "VGGFace", "VGGFace2", "ArcFace"] = Field(
        default="ArcFace",
        description="Normalization technique"
    )
    
    # Tracker settings
    tracker_max_age: int = Field(default=30, ge=1, description="Max frames to keep lost tracks")
    tracker_min_hits: int = Field(default=3, ge=1, description="Min detections before track is confirmed")
    tracker_iou_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="IOU threshold for matching")
    recognition_repeat_frames: int = Field(default=60, ge=10, description="Re-recognize after N frames (2 sec @ 30fps)")
    
    # Processing settings
    embedding_dim: int = Field(default=512, ge=128, description="Embedding dimension (512 for ArcFace)")
    max_batch_size: int = Field(default=8, ge=1, le=32, description="Max batch size for inference")
    
    # Cache settings
    embedding_cache_size: int = Field(default=1000, ge=10, description="LRU cache size for embeddings")
    
    # Enrollment database path
    enrollment_db_path: str = Field(default="./storage/enrollments.db", description="Path to enrollment database")
    
    # Model cache path (for DeepFace model weights)
    deepface_home: str = Field(default="./storage/.deepface", description="DeepFace model cache directory")
    
    # RTSP Camera Stream (for testing)
    test_rtsp_stream: str = Field(
        default="rtsp://admin:admin123@192.168.128.10:554/avstream/channel=1/stream=0.sdp",
        description="Test RTSP camera stream URL"
    )
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", description="Log level")
    
    @field_validator("internal_service_token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate internal service token is set."""
        if v == "change_me_in_production":
            import logging
            logging.warning("⚠️  WARNING: Using default internal service token - CHANGE IN PRODUCTION!")
        return v


# Global config instance
config = ModelServerConfig()
