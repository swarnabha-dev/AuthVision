"""
Configuration management for main backend.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


# Get absolute path to main_backend directory
MAIN_BACKEND_DIR = Path(__file__).parent.parent.resolve()
STORAGE_DIR = MAIN_BACKEND_DIR / "storage"
DB_FILE = STORAGE_DIR / "main_backend.db"


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    debug: bool = True
    
    # Database (absolute path to avoid ambiguity)
    database_url: str = f"sqlite+aiosqlite:///{DB_FILE}"
    
    # JWT
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    
    # Model Server (using Field with alias to avoid Pydantic namespace conflict)
    model_server_url: str = "http://localhost:8001"
    model_server_username: str = "backend_service"
    model_server_password: str = "SecurePassword123!"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        protected_namespaces=()  # Disable protected namespace warnings
    )
    
    # RTSP Configuration
    rtsp_streams: str = ""  # Comma-separated RTSP URLs
    motion_detection_threshold: int = 500
    keyframe_interval: int = 30
    process_every_n_frames: int = 5
    
    # Storage (absolute paths)
    photos_dir: str = str(STORAGE_DIR / "photos")
    frames_cache_dir: str = str(STORAGE_DIR / "frames_cache")
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def db_path(self) -> Path:
        """Get absolute path to database file."""
        return DB_FILE
    
    @property
    def storage_dir(self) -> Path:
        """Get absolute path to storage directory."""
        return STORAGE_DIR
    
    @property
    def rtsp_stream_list(self) -> List[str]:
        """Parse RTSP streams from comma-separated string."""
        if not self.rtsp_streams:
            return []
        return [s.strip() for s in self.rtsp_streams.split(",") if s.strip()]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


# Global settings instance
settings = Settings()
