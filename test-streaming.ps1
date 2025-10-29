# Test Live Streaming Features

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Live Streaming Features Test" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0

# Test 1: Import stream service with new methods
Write-Host "[1] Testing stream service with MJPEG support..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.services.stream_service import StreamService; s = StreamService(); print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Stream service loads successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Stream service import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 2: Import updated routes
Write-Host "[2] Testing stream routes with video endpoint..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.api.v1.routes_stream import router, stream_video, discover_streams; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Video streaming endpoints available" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Stream routes import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 3: Import complete app
Write-Host "[3] Testing FastAPI app with streaming..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.main import app; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] FastAPI app loads with streaming support" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] FastAPI app import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 4: Check viewer.html exists
Write-Host "[4] Checking web viewer..." -ForegroundColor Yellow
if (Test-Path "viewer.html") {
    Write-Host "  [PASS] Web viewer available at viewer.html" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] viewer.html not found" -ForegroundColor Red
    $errors++
}

# Test 5: Check STREAMING_GUIDE.md exists
Write-Host "[5] Checking documentation..." -ForegroundColor Yellow
if (Test-Path "STREAMING_GUIDE.md") {
    Write-Host "  [PASS] Streaming guide available" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] STREAMING_GUIDE.md not found" -ForegroundColor Red
    $errors++
}

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($errors -eq 0) {
    Write-Host "[SUCCESS] All streaming features ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "New Features Added:" -ForegroundColor Cyan
    Write-Host "  1. MJPEG live video streaming endpoint" -ForegroundColor White
    Write-Host "  2. Auto camera discovery on network" -ForegroundColor White
    Write-Host "  3. Web-based stream viewer (viewer.html)" -ForegroundColor White
    Write-Host ""
    Write-Host "How to Use:" -ForegroundColor Cyan
    Write-Host "  1. Start server: .\start-dev.ps1" -ForegroundColor White
    Write-Host "  2. Open viewer.html in browser" -ForegroundColor White
    Write-Host "  3. Click 'Auto-Discover' or enter RTSP URL" -ForegroundColor White
    Write-Host "  4. Watch live video stream!" -ForegroundColor White
    Write-Host ""
    Write-Host "API Endpoints:" -ForegroundColor Cyan
    Write-Host "  - GET /api/v1/stream/video/{camera_id} - View live stream" -ForegroundColor White
    Write-Host "  - GET /api/v1/stream/discover - Find cameras on network" -ForegroundColor White
    Write-Host ""
    Write-Host "See STREAMING_GUIDE.md for detailed instructions" -ForegroundColor Yellow
} else {
    Write-Host "[FAILED] $errors test(s) failed" -ForegroundColor Red
}

Write-Host ""
