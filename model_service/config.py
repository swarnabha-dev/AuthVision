import os

# ---------------------------------------
# PROJECT ROOT
# ---------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------
# DEEPFACE MODEL WEIGHTS DIRECTORY
# ---------------------------------------
DEEPFACE_HOME = os.path.join(BASE_DIR, "deepface_models")
os.makedirs(DEEPFACE_HOME, exist_ok=True)

# This env variable controls DeepFace weight loading
os.environ["DEEPFACE_HOME"] = DEEPFACE_HOME


# ---------------------------------------
# ARC FACE DATABASE DIRECTORY
# ---------------------------------------
ARC_DB_DIR = os.path.join(BASE_DIR, "arcface_db")
os.makedirs(ARC_DB_DIR, exist_ok=True)




# ---------------------------------------
# DEFAULT DEEPFACE PARAMETERS
# ---------------------------------------
MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "yolov8n"
NORMALIZATION = "ArcFace"
ANTI_SPOOFING = True
ALIGN = True
THRESHOLD = 0.4
BATCHED = True
REFRESH_DATABASE = False  # DeepFace will ignore when ArcFace refresh logic is patched
DISTANCE_METRIC = "cosine"


# ---------------------------------------
# SERVER SETTINGS
# ---------------------------------------
MAX_UPLOAD_SIZE_MB = 10


# DeepFace PKL convention (MUST MATCH DEEPFACE FORMAT)
# Build the filename dynamically from the configured variables above so it reflects
# the detector backend, whether images are aligned, and the normalization method.
# Example result: ds_model_arcface_detector_yolov8n_aligned_normalization_arcface_expand_0.pkl
_aligned_part = "aligned" if ALIGN else "unaligned"
_normalization_part = (NORMALIZATION.lower() if isinstance(NORMALIZATION, str) else "arcface")
ARC_PKL_NAME = f"ds_model_arcface_detector_{DETECTOR_BACKEND}_{_aligned_part}_normalization_{_normalization_part}_expand_0.pkl"

ARC_PKL_PATH = os.path.join(ARC_DB_DIR, ARC_PKL_NAME)

# ---------------------------------------
# AUTH / DATABASE
# ---------------------------------------
# Database URL for auth (SQLAlchemy). Defaults to sqlite file under BASE_DIR.
AUTH_DATABASE_URL = os.environ.get("AUTH_DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'auth.db')}")

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRES_SECONDS = int(os.environ.get("ACCESS_TOKEN_EXPIRES_SECONDS", 900))
REFRESH_TOKEN_EXPIRES_SECONDS = int(os.environ.get("REFRESH_TOKEN_EXPIRES_SECONDS", 60 * 60 * 24 * 7))

# API key settings
API_KEY_BYTES = int(os.environ.get("API_KEY_BYTES", 32))