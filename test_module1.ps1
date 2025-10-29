# Module 1 Validation Script
# Tests basic imports and structure

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Module 1 Validation Tests" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0

# Test 1: Import app.main
Write-Host "[1] Testing app.main import..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); from app.main import app; print('OK')" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] app.main imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] app.main import failed" -ForegroundColor Red
        $errors++
    }
} catch {
    Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    $errors++
}

# Test 2: Import all routes
Write-Host "[2] Testing route imports..." -ForegroundColor Yellow
$routes = @(
    "app.api.v1.routes_health",
    "app.api.v1.routes_device",
    "app.api.v1.routes_models",
    "app.api.v1.routes_stream",
    "app.api.v1.routes_attendance"
)

foreach ($route in $routes) {
    try {
        & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import $route" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [PASS] $route" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $route" -ForegroundColor Red
            $errors++
        }
    } catch {
        Write-Host "  [FAIL] $route - $($_.Exception.Message)" -ForegroundColor Red
        $errors++
    }
}

# Test 3: Import all services
Write-Host "[3] Testing service imports..." -ForegroundColor Yellow
$services = @(
    "app.services.detector_service",
    "app.services.embedding_service",
    "app.services.matcher_service",
    "app.services.pose_service",
    "app.services.pafu_service",
    "app.services.tracker_service",
    "app.services.stream_service",
    "app.services.attendance_service"
)

foreach ($service in $services) {
    try {
        & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import $service" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [PASS] $service" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $service" -ForegroundColor Red
            $errors++
        }
    } catch {
        Write-Host "  [FAIL] $service - $($_.Exception.Message)" -ForegroundColor Red
        $errors++
    }
}

# Test 4: Import all models
Write-Host "[4] Testing model imports..." -ForegroundColor Yellow
$models = @(
    "app.models.config",
    "app.models.detection_models",
    "app.models.stream_models",
    "app.models.attendance_models"
)

foreach ($model in $models) {
    try {
        & .\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'src'); import $model" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [PASS] $model" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] $model" -ForegroundColor Red
            $errors++
        }
    } catch {
        Write-Host "  [FAIL] $model - $($_.Exception.Message)" -ForegroundColor Red
        $errors++
    }
}

# Test 5: Run pytest
Write-Host "[5] Running pytest unit tests..." -ForegroundColor Yellow
try {
    $env:PYTHONPATH = "src"
    $output = & .\venv\Scripts\python.exe -m pytest tests/unit/test_routes.py -v --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [PASS] All unit tests passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Some tests failed" -ForegroundColor Red
        Write-Host $output -ForegroundColor Gray
        $errors++
    }
} catch {
    Write-Host "  [FAIL] pytest execution failed" -ForegroundColor Red
    $errors++
}

# Summary
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

if ($errors -eq 0) {
    Write-Host "[SUCCESS] Module 1 validation passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start server: .\start-dev.ps1" -ForegroundColor White
    Write-Host "  2. Visit API docs: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  3. Test endpoints manually in Swagger UI" -ForegroundColor White
    Write-Host "  4. Reply: 'Module 1 validated, proceed to Module 2'" -ForegroundColor White
} else {
    Write-Host "[FAILED] $errors validation error(s) found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the errors before proceeding to Module 2" -ForegroundColor Yellow
}

Write-Host ""
