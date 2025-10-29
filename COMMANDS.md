# 🚀 Quick Commands Reference

## ⚡ Start Server

### Production Mode
```powershell
.\start-server.ps1
```
- Production-ready configuration
- Proper Python path handling

### Development Mode (Recommended)
```powershell
.\start-dev.ps1
```
- Development configuration
- Proper Python path handling

### Manual Start (Alternative)
```powershell
# Direct Python launcher (handles imports automatically)
.\venv\Scripts\python.exe run_server.py
```

## 🧪 Testing

### Run Unit Tests
```powershell
# All tests
pytest tests/unit/test_routes.py -v

# With coverage
pytest tests/unit/test_routes.py --cov=src --cov-report=html
```

### Test API (server must be running)
```powershell
.\test-api.ps1
```

### Validate Installation
```powershell
.\validate.ps1
```

## 🔧 Setup

### First Time Setup
```powershell
.\setup.ps1
```

### Manual Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

## 🌐 Access Points

- **API Docs (Interactive)**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | System health check |
| `/api/v1/devices/register` | POST | Register edge device |
| `/api/v1/stream/start` | POST | Start RTSP stream |
| `/api/v1/stream/stop` | POST | Stop RTSP stream |
| `/api/v1/models` | GET | List available models |
| `/api/v1/models/activate` | POST | Activate model version |
| `/api/v1/attendance/enroll` | POST | Enroll student (multipart) |
| `/api/v1/attendance` | GET | Query attendance records |

## 🔍 Troubleshooting

### "Module not found" error
**Fixed!** Use the new startup scripts:
```powershell
.\start-dev.ps1
```

The scripts automatically set `PYTHONPATH=src` so imports work correctly.

### Server won't start
```powershell
# Check if virtual environment exists
Test-Path venv

# Reinstall if needed
.\setup.ps1
```

### Tests fail
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run tests
pytest tests/unit/test_routes.py -v
```

## 📊 Common Workflows

### Development Workflow
```powershell
# 1. Start dev server (one terminal)
.\start-dev.ps1

# 2. Make code changes (files auto-reload)

# 3. Test API (another terminal)
.\test-api.ps1
```

### Testing Workflow
```powershell
# 1. Run unit tests
pytest tests/unit/test_routes.py -v

# 2. Start server
.\start-dev.ps1

# 3. Test API endpoints
.\test-api.ps1
```

## 🎯 What Changed (Fix for Module Import Error)

### Problem
```
ModuleNotFoundError: No module named 'app'
```

### Solution
Created startup scripts that automatically set `PYTHONPATH`:
- `start-server.ps1` - Production mode
- `start-dev.ps1` - Development mode with auto-reload

### What the Scripts Do
```powershell
$env:PYTHONPATH = "src"  # Tells Python where to find 'app' module
hypercorn app.main:app   # Now imports work correctly
```

## ✅ Validation Checklist

- [ ] Run `.\setup.ps1` (if first time)
- [ ] Run `.\validate.ps1` (all checks pass)
- [ ] Run `.\start-dev.ps1` (server starts)
- [ ] Visit http://localhost:8000/docs (interactive docs load)
- [ ] Run `.\test-api.ps1` (all API tests pass)

## 📚 Key Files

| File | Purpose |
|------|---------|
| `start-dev.ps1` | ⭐ Start development server (auto-reload) |
| `start-server.ps1` | Start production server |
| `test-api.ps1` | Test all API endpoints |
| `validate.ps1` | Validate installation |
| `setup.ps1` | First-time setup |

## 💡 Pro Tips

1. **Always use `start-dev.ps1` during development** - it auto-reloads on code changes
2. **Keep the server running** - test changes in real-time at http://localhost:8000/docs
3. **Check logs** - errors appear in the terminal where server is running
4. **Use API docs** - http://localhost:8000/docs for interactive testing

---

**Next: Start the server and validate Module 1**

```powershell
# Terminal 1: Start server
.\start-dev.ps1

# Terminal 2: Test API
.\test-api.ps1
```

Then confirm: **"Module 1 validated, proceed to Module 2"**
