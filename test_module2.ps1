# Module 2 Validation Script
# Tests RTSP stream acquisition and BAFS scheduler

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Module 2 Validation Tests" -ForegroundColor Cyan
Write-Host "RTSP Streams + BAFS Scheduler" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0

# Test 1: Import RTSP models
Write-Host "[1] Testing RTSP models import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.models.rtsp_models import Frame, RTSPConfig, BAFSConfig, StreamStats; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] RTSP models import successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] RTSP models import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 2: Import BAFS scheduler
Write-Host "[2] Testing BAFS scheduler import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.services.bafs_scheduler import BAFSScheduler, get_bafs_scheduler; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] BAFS scheduler imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] BAFS scheduler import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 3: Import frame queue
Write-Host "[3] Testing frame queue import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.services.frame_queue import FrameQueue, FrameQueueManager; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Frame queue imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Frame queue import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 4: Import RTSP client
Write-Host "[4] Testing RTSP client import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.services.rtsp_client import RTSPClient, RTSPClientManager; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] RTSP client imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] RTSP client import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 5: Import updated stream service
Write-Host "[5] Testing updated stream service import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.services.stream_service import StreamService, get_stream_service; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Stream service imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Stream service import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 6: Import updated stream routes
Write-Host "[6] Testing updated stream routes import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.api.v1.routes_stream import router; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Stream routes import successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Stream routes import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 7: Run BAFS unit tests
Write-Host "[7] Running BAFS scheduler unit tests..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = "src"
    $output = & .\venv\Scripts\python.exe -m pytest tests/unit/test_bafs.py -v --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] BAFS tests passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] BAFS tests failed" -ForegroundColor Red
        Write-Host $output -ForegroundColor Gray
        $errors++
    }
} catch {
    Write-Host "  [FAIL] BAFS test execution failed" -ForegroundColor Red
    $errors++
}

# Test 8: Run frame queue unit tests
Write-Host "[8] Running frame queue unit tests..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = "src"
    $output = & .\venv\Scripts\python.exe -m pytest tests/unit/test_frame_queue.py -v --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] Frame queue tests passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Frame queue tests failed" -ForegroundColor Red
        Write-Host $output -ForegroundColor Gray
        $errors++
    }
} catch {
    Write-Host "  [FAIL] Frame queue test execution failed" -ForegroundColor Red
    $errors++
}

# Test 9: Verify OpenCV dependency
Write-Host "[9] Verifying OpenCV installation..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import cv2; print(f'OpenCV {cv2.__version__}')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] OpenCV is installed and working" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] OpenCV not found" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] OpenCV verification failed" -ForegroundColor Red
    $errors++
}

# Test 10: Verify numpy dependency
Write-Host "[10] Verifying numpy installation..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import numpy; print(f'NumPy {numpy.__version__}')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] NumPy is installed and working" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] NumPy not found" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] NumPy verification failed" -ForegroundColor Red
    $errors++
}

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($errors -eq 0) {
    Write-Host "[SUCCESS] Module 2 validation passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Module 2 Features Implemented:" -ForegroundColor Cyan
    Write-Host "  - RTSP stream capture with OpenCV" -ForegroundColor White
    Write-Host "  - Auto-reconnection on stream failures" -ForegroundColor White
    Write-Host "  - Thread-safe frame queuing with overflow handling" -ForegroundColor White
    Write-Host "  - BAFS (Budget-Aware Frame Scheduler)" -ForegroundColor White
    Write-Host "  - Dynamic FPS allocation based on priority" -ForegroundColor White
    Write-Host "  - Stream management service integration" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start server: .\start-dev.ps1" -ForegroundColor White
    Write-Host "  2. Test stream endpoints at /docs" -ForegroundColor White
    Write-Host "  3. Reply: 'Module 2 validated, proceed to Module 3'" -ForegroundColor White
} else {
    Write-Host "[FAILED] $errors validation error(s) found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the errors before proceeding to Module 3" -ForegroundColor Yellow
}

Write-Host ""
