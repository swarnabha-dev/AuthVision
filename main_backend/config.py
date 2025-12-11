import os
from pathlib import Path
from datetime import timedelta


# Database (SQLite file in working dir by default)
BASE_DIR = Path(os.environ.get("MAIN_BACKEND_HOME", Path.cwd() / "main_backend_data"))
BASE_DIR.mkdir(parents=True, exist_ok=True)

# Departments config
DEPARTMENTS = ["CSE", "ECE", "MECH", "EEE", "CIVIL", "Bio-Tech"]

SQLALCHEMY_DATABASE_URL = os.environ.get("MAIN_BACKEND_DATABASE_URL") or f"sqlite:///{BASE_DIR / 'main_backend.db'}"

# JWT settings
JWT_SECRET = os.environ.get("MAIN_BACKEND_JWT_SECRET", "change-me-in-prod")
JWT_ALGORITHM = os.environ.get("MAIN_BACKEND_JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_SECONDS = int(os.environ.get("MAIN_BACKEND_ACCESS_EXPIRES", 3600))
REFRESH_TOKEN_EXPIRES_SECONDS = int(os.environ.get("MAIN_BACKEND_REFRESH_EXPIRES", 60 * 60 * 24 * 30))

# Model layer (external) base url
MODEL_SERVICE_URL = os.environ.get("MODEL_SERVICE_URL", "http://localhost:8080")

# Model service auth (main_backend should call model_service using these)
MODEL_SERVICE_API_KEY = os.environ.get("MODEL_SERVICE_API_KEY")
MODEL_SERVICE_ACCESS_TOKEN = os.environ.get("MODEL_SERVICE_ACCESS_TOKEN")
# Auto-auth credentials for model service (if provided, main_backend will register/login automatically)
MODEL_SERVICE_AUTO_AUTH = os.environ.get("MODEL_SERVICE_AUTO_AUTH", "1") in ("1", "true", "True")
MODEL_SERVICE_USER = os.environ.get("MODEL_SERVICE_USER", "main_backend_bot")
MODEL_SERVICE_PASS = os.environ.get("MODEL_SERVICE_PASS", "change-me")
# seconds before expiry to proactively refresh
MODEL_SERVICE_REFRESH_MARGIN = int(os.environ.get("MODEL_SERVICE_REFRESH_MARGIN", 30))

# Stream defaults
DEFAULT_KEYFRAME_INTERVAL = int(os.environ.get("MAIN_BACKEND_KEYFRAME_INTERVAL", 10))  # send every N frames to model
