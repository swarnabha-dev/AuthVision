# Quick Start Guide (Windows PowerShell)

## Prerequisites
- Python 3.12.8 installed
- PowerShell 5.1 or later
- Git (optional)

## Step 1: Setup (Choose One Method)

### Method A: Automated Setup (Recommended)
```powershell
# Run the setup script
.\setup.ps1
```

### Method B: Manual Setup
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment
```powershell
# Copy example config
Copy-Item .env.example .env

# Edit with your settings (optional for testing)
notepad .env
```

## Step 3: Run Tests
```powershell
# Run all unit tests
pytest tests/unit/test_routes.py -v

# Expected output: 15+ tests pass, 0 failures
```

## Step 4: Start Server
```powershell
# Production server (hypercorn)
hypercorn src.app.main:app --bind 0.0.0.0:8000 --workers 1 --log-level info

# Development server (with auto-reload)
hypercorn src.app.main:app --bind 0.0.0.0:8000 --reload
```

## Step 5: Test API

### Browser
Open http://localhost:8000/docs for interactive API documentation.

### PowerShell
```powershell
# Health check
Invoke-RestMethod -Uri http://localhost:8000/api/v1/health -Method Get

# Should return:
# status        : healthy
# timestamp     : 2025-10-27T...Z
# uptime_seconds: 0.123
```

## Common Commands

### Run tests with coverage
```powershell
pytest tests/unit/test_routes.py --cov=src --cov-report=html
# View coverage: .\htmlcov\index.html
```

### Type checking
```powershell
mypy src/ --strict
```

### Code formatting
```powershell
# Check formatting
black --check src/ tests/

# Format code
black src/ tests/
```

### Import sorting
```powershell
# Check imports
isort --check-only src/ tests/

# Sort imports
isort src/ tests/
```

## Troubleshooting

### "Python not found"
Ensure Python 3.12.8 is installed and in PATH:
```powershell
python --version
# Should show: Python 3.12.8
```

### "Cannot activate virtual environment"
Enable script execution:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "Module not found"
Ensure virtual environment is activated:
```powershell
# You should see (venv) in your prompt
.\venv\Scripts\Activate.ps1
```

### "Tests fail"
Ensure dependencies are installed:
```powershell
pip install -r requirements.txt
```

## API Endpoints (Module 1)

All endpoints return stub/dummy data:

- `GET /api/v1/health` - System health
- `POST /api/v1/devices/register` - Register device
- `POST /api/v1/stream/start` - Start stream (stub)
- `POST /api/v1/stream/stop` - Stop stream (stub)
- `GET /api/v1/models` - List models (stub)
- `POST /api/v1/models/activate` - Activate model (stub)
- `POST /api/v1/attendance/enroll` - Enroll student (stub)
- `GET /api/v1/attendance` - Query attendance (stub)

## Next Steps

After validating Module 1:
1. Confirm all tests pass
2. Confirm server starts and responds
3. Review VALIDATION_CHECKLIST.md
4. **Inform the agent to proceed to Module 2**

## Module 2 Preview

Next module will implement:
- RTSP stream capture
- Frame queue management
- BAFS keyframe scheduler

**Do not proceed until Module 1 is validated!**
