# Smart Attendance System - Production Grade

## Overview
A production-grade, modular, CPU-first (GPU-scalable) Smart Attendance system with MLflow orchestration.

**Pipeline**: RTSP → BAFS keyframe scheduler → detection → pose → PAFU (hybrid FFWM+FSPFM embedding-level) →
AdaFace recognition (pretrained) + periocular + ReID → PaMIE fusion → tracking → matching → attendance logging

## Tech Stack
- Python 3.12.8
- FastAPI with Pydantic v2 strict typing
- Hypercorn ASGI server
- ONNX Runtime (CPU primary, GPU scalable)
- MLflow (experiments, model registry, retrain pipelines)
- SQLite (encrypted local storage)

## Current Implementation Status

### ✅ Module 1: FastAPI Skeleton (COMPLETED)
- Typed Pydantic v2 models with strict typing
- Dependency-injected service stubs
- Complete API routes under `/api/v1`
- Unit tests with FastAPI TestClient

### ✅ Module 2: RTSP Streams + BAFS Scheduler (COMPLETED)
- RTSP stream capture with OpenCV
- Auto-reconnection on failures
- Thread-safe frame queue with overflow handling
- **BAFS scheduler**: Dynamic FPS allocation based on priority
- **MJPEG streaming**: View live video in browser
- **Auto camera discovery**: Find RTSP cameras on network
- Web-based stream viewer (viewer.html)

### 🔲 Module 3-16: Pipeline Components (TODO)
See PIPELINE MODULE ORDER in project documentation.

## Key Features (Planned)

### BAFS Scheduler
- Motion estimation + yaw/orientation-based frame selection
- Keyframes for full detector + face pipeline
- Lightframes for periocular/ReID only
- Best-frame-in-window API (1-2s lookback)

### AdaFace Integration
- Primary recognition module for frontal faces (yaw < 20°)
- Auto-fetch pretrained weights from https://github.com/mk-minchul/AdaFace
- Integrated into PaMIE fusion pipeline

### Automatic Model Fetching
- Auto-download and verify (SHA256) pretrained models
- ONNX conversion and INT8 quantization
- MLflow model registry integration

## Quick Start

### Automated Setup (Recommended)
```powershell
# Run automated setup
.\setup.ps1

# Validate installation
.\validate.ps1
```

### Manual Setup

#### 1. Setup Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Configure Environment
```powershell
# Copy example config
Copy-Item .env.example .env

# Edit .env with your settings (optional for testing)
notepad .env
```

#### 3. Run Tests
```powershell
# Run all unit tests
pytest tests/unit/test_routes.py -v

# Run with coverage
pytest tests/unit/test_routes.py --cov=src --cov-report=html

# Expected: 15+ tests pass, 0 failures
```

#### 4. Start Development Server
```powershell
# Using hypercorn (production ASGI server)
hypercorn src.app.main:app --bind 0.0.0.0:8000 --workers 1 --log-level info

# Or for development with auto-reload
hypercorn src.app.main:app --bind 0.0.0.0:8000 --reload
```

#### 5. Test API
```powershell
# Automated API testing (server must be running)
.\test-api.ps1

# Manual browser testing
# Visit: http://localhost:8000/docs
```

### Access Points
- **API Base**: http://localhost:8000/api/v1
- **Health Check**: http://localhost:8000/api/v1/health
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### Health
- `GET /api/v1/health` - System health status

### Device Management
- `POST /api/v1/devices/register` - Register edge device

### Stream Management
- `POST /api/v1/stream/start` - Start RTSP stream processing
- `POST /api/v1/stream/stop` - Stop stream processing

### Model Management
- `GET /api/v1/models` - List available models
- `POST /api/v1/models/activate` - Activate model version

### Enrollment
- `POST /api/v1/enroll` - Enroll student (multipart form)

### Attendance
- `GET /api/v1/attendance` - Query attendance records

## Development Guidelines

### Module-by-Module Development
**CRITICAL**: Modules must be implemented in strict order. Do not proceed to the next module until:
1. Current module code is complete
2. Unit tests pass
3. User confirms module completion

### Type Safety
- All models use Pydantic v2 with `ConfigDict(strict=True)`
- No `typing.Any` or ambiguous types
- Return concrete types only

### Testing
- Unit tests for each module (pytest)
- Integration tests for combined steps
- CI/CD with mypy, black, isort checks

## Project Structure
```
smart-attendance/
├── src/
│   ├── app/              # FastAPI application
│   ├── pipeline/         # Processing pipeline (stubs)
│   ├── mlflow/          # MLflow integration (stubs)
│   └── utils/           # Shared utilities
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── docker/              # Container configs
├── infra/               # K8s manifests
└── scripts/             # Build/deploy scripts
```

## Next Steps
1. ✅ Validate FastAPI skeleton and tests
2. ⏳ Implement Module 2: RTSP + BAFS scheduler
3. ⏳ Implement Module 3: YOLOv10-tiny detector
4. ⏳ Continue through pipeline modules in order

## License
TBD

## Contributors
TBD
