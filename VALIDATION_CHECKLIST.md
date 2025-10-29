# Module 1 Validation Checklist

## ✅ Files Created

### Core Application
- [x] `src/app/main.py` - FastAPI application
- [x] `src/app/deps.py` - Dependency injection
- [x] `src/app/models/config.py` - Pydantic v2 config
- [x] `src/app/models/stream_models.py` - Stream models
- [x] `src/app/models/detection_models.py` - Detection models
- [x] `src/app/models/attendance_models.py` - Attendance models

### API Routes (all under `/api/v1`)
- [x] `src/app/api/v1/routes_health.py` - Health endpoint
- [x] `src/app/api/v1/routes_device.py` - Device registration
- [x] `src/app/api/v1/routes_models.py` - Model management
- [x] `src/app/api/v1/routes_stream.py` - Stream management
- [x] `src/app/api/v1/routes_attendance.py` - Attendance & enrollment

### Services (stubs)
- [x] `src/app/services/stream_service.py`
- [x] `src/app/services/detector_service.py`
- [x] `src/app/services/pose_service.py`
- [x] `src/app/services/embedding_service.py`
- [x] `src/app/services/pafu_service.py`
- [x] `src/app/services/tracker_service.py`
- [x] `src/app/services/matcher_service.py`
- [x] `src/app/services/attendance_service.py`

### Utilities (stubs)
- [x] `src/utils/downloads.py` - Model downloader
- [x] `src/utils/security.py` - Security utilities
- [x] `src/utils/timers.py` - Performance timing
- [x] `src/utils/logging.py` - Structured logging

### Tests
- [x] `tests/unit/test_routes.py` - Comprehensive route tests

### Configuration
- [x] `pyproject.toml` - Project metadata
- [x] `requirements.txt` - Dependencies
- [x] `.env.example` - Environment template
- [x] `MLproject` - MLflow config
- [x] `conda.yaml` - Conda environment
- [x] `.gitignore` - Git ignore rules

### Infrastructure (stubs)
- [x] `docker/Dockerfile.edge`
- [x] `docker/Dockerfile.server`
- [x] `infra/k8s_deploy.yaml`
- [x] `infra/canary_rollout.yaml`

### Scripts (stubs)
- [x] `scripts/export_onnx.sh`
- [x] `scripts/quantize_onnx.sh`
- [x] `scripts/sign_model.sh`
- [x] `scripts/deploy_canary.sh`

### CI/CD
- [x] `.github/workflows/ci.yml`

## 🧪 Testing Instructions

### 1. Setup Environment
```powershell
# Run setup script
.\setup.ps1

# OR manually:
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Copy Environment Config
```powershell
Copy-Item .env.example .env
```

### 3. Run Unit Tests
```powershell
# All tests with verbose output
.\venv\Scripts\python.exe -m pytest tests/unit/test_routes.py -v

# With coverage report
.\venv\Scripts\python.exe -m pytest tests/unit/test_routes.py -v --cov=src --cov-report=html

# Expected output: All tests pass (8 test classes, ~15 tests total)
```

### 4. Start Development Server
```powershell
# Using hypercorn (production ASGI server)
.\venv\Scripts\hypercorn.exe src.app.main:app --bind 0.0.0.0:8000 --workers 1 --log-level info

# OR with auto-reload for development
.\venv\Scripts\hypercorn.exe src.app.main:app --bind 0.0.0.0:8000 --reload
```

### 5. Test API Endpoints

#### Via Browser
- Interactive Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

#### Via PowerShell (Invoke-RestMethod)
```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8000/api/v1/health -Method Get

# Register device
$body = @{
    device_id = "edge-001"
    model = "jetson-nano"
    location = "lab-entrance"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/api/v1/devices/register -Method Post -Body $body -ContentType "application/json"

# List models
Invoke-RestMethod -Uri http://localhost:8000/api/v1/models -Method Get

# Query attendance
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/attendance?camera_id=cam-001&date=2025-10-27" -Method Get
```

## ✅ Expected Behavior

### All Routes Return Stub Data
- ✅ Health: Returns status, timestamp, uptime
- ✅ Device registration: Returns "registered" status
- ✅ Stream start/stop: Returns stub messages (RTSP not implemented)
- ✅ Models list: Returns 2 dummy models (yolov10-tiny, adaface)
- ✅ Model activate: Returns success stub
- ✅ Enrollment: Returns stub embedding_id
- ✅ Attendance query: Returns 1 stub record

### All Responses Use Strict Typing
- ✅ No `typing.Any` in code
- ✅ Pydantic v2 models with `ConfigDict(strict=True)`
- ✅ All fields properly typed (str, int, float, bool, list)

### Unit Tests
- ✅ All 8 test classes pass
- ✅ Type validation works (422 on missing fields)
- ✅ Timestamps are ISO 8601 format
- ✅ Confidence values are 0.0-1.0 range
- ✅ Multipart file upload works (enrollment)

## 🔲 Known Limitations (Expected)

These are **intentional** for Module 1:
- ❌ No RTSP streaming (Module 2)
- ❌ No BAFS scheduler (Module 2)
- ❌ No detection (Module 3)
- ❌ No pose estimation (Module 4)
- ❌ No embedding extraction (Modules 5-7)
- ❌ No tracking (Module 10)
- ❌ No matching (Module 11)
- ❌ No database persistence (Module 12)
- ❌ No MLflow integration (Module 14)
- ❌ Service stubs raise NotImplementedError (except stream/attendance which return dummy data)

## 📋 Module 1 Completion Criteria

Before proceeding to Module 2, verify:
- [ ] All unit tests pass
- [ ] FastAPI server starts without errors
- [ ] All 8 routes return typed responses
- [ ] Interactive docs work at /docs
- [ ] .env file created from .env.example
- [ ] Virtual environment activated
- [ ] No import errors when running tests

## ➡️ Next Steps (After User Confirmation)

**Module 2: Frame Ingestion**
- Implement RTSP capture service (`src/pipeline/io/rtsp_reader.py`)
- Implement frame queue (`src/pipeline/io/frame_queue.py`)
- Implement BAFS scheduler (`src/pipeline/bafs/bafs_scheduler.py`)
- Unit tests for each component
- Integration test: RTSP → frame queue → keyframe selection

**DO NOT proceed to Module 2 until user confirms Module 1 is validated.**
