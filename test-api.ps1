# API Testing Script for Smart Attendance
# Run this after starting the server to test all endpoints

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Smart Attendance - API Tests" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000"
$errors = 0

# Check if server is running
Write-Host "[0] Checking if server is running..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/api/v1/health" -Method Get -ErrorAction Stop
    Write-Host "  ✓ Server is running" -ForegroundColor Green
    Write-Host "    Status: $($health.status)" -ForegroundColor Gray
    Write-Host "    Uptime: $([math]::Round($health.uptime_seconds, 2))s" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Server is not running" -ForegroundColor Red
    Write-Host "    Start with: .\venv\Scripts\hypercorn.exe src.app.main:app --bind 0.0.0.0:8000" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Test 1: Health endpoint
Write-Host "[1] Testing GET /api/v1/health" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/health" -Method Get
    Write-Host "  ✓ Response: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 2: Device registration
Write-Host "[2] Testing POST /api/v1/devices/register" -ForegroundColor Yellow
try {
    $body = @{
        device_id = "edge-test-001"
        model = "jetson-nano"
        location = "test-lab"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/devices/register" -Method Post -Body $body -ContentType "application/json"
    Write-Host "  ✓ Device registered: $($response.device_id)" -ForegroundColor Green
    Write-Host "    Status: $($response.status)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 3: List models
Write-Host "[3] Testing GET /api/v1/models" -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/models" -Method Get
    Write-Host "  ✓ Found $($response.models.Count) models" -ForegroundColor Green
    foreach ($model in $response.models) {
        Write-Host "    - $($model.name) v$($model.version) [$($model.stage)]" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 4: Activate model
Write-Host "[4] Testing POST /api/v1/models/activate" -ForegroundColor Yellow
try {
    $body = @{
        name = "yolov10-tiny"
        version = "1.0.0"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/models/activate" -Method Post -Body $body -ContentType "application/json"
    Write-Host "  ✓ Model activation: $($response.success)" -ForegroundColor Green
    Write-Host "    Message: $($response.message)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 5: Start stream
Write-Host "[5] Testing POST /api/v1/stream/start" -ForegroundColor Yellow
try {
    $body = @{
        camera_id = "cam-test-001"
        rtsp_url = "rtsp://192.168.1.100:554/stream"
        config_name = "default"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/stream/start" -Method Post -Body $body -ContentType "application/json"
    Write-Host "  ✓ Stream started: $($response.started)" -ForegroundColor Green
    Write-Host "    Message: $($response.message)" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 6: Stop stream
Write-Host "[6] Testing POST /api/v1/stream/stop" -ForegroundColor Yellow
try {
    $body = @{
        camera_id = "cam-test-001"
    } | ConvertTo-Json
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/stream/stop" -Method Post -Body $body -ContentType "application/json"
    Write-Host "  ✓ Stream stopped: $($response.stopped)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 7: Query attendance
Write-Host "[7] Testing GET /api/v1/attendance" -ForegroundColor Yellow
try {
    $params = @{
        camera_id = "cam-test-001"
        date = "2025-10-27"
    }
    
    $response = Invoke-RestMethod -Uri "$baseUrl/api/v1/attendance" -Method Get -Body $params
    Write-Host "  ✓ Found $($response.records.Count) attendance record(s)" -ForegroundColor Green
    if ($response.records.Count -gt 0) {
        Write-Host "    Student: $($response.records[0].student_id)" -ForegroundColor Gray
        Write-Host "    Confidence: $($response.records[0].confidence)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ Failed" -ForegroundColor Red
    $errors++
}

# Test 8: Enrollment (multipart) - requires file
Write-Host "[8] Testing POST /api/v1/attendance/enroll (skipped - requires image file)" -ForegroundColor Yellow
Write-Host "    Use interactive docs at /docs to test this endpoint" -ForegroundColor Gray

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

if ($errors -eq 0) {
    Write-Host "✓ All API tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Additional testing:" -ForegroundColor Cyan
    Write-Host "  - Visit http://localhost:8000/docs for interactive testing" -ForegroundColor White
    Write-Host "  - Test enrollment endpoint with image upload" -ForegroundColor White
    Write-Host "  - Review API responses for correct typing" -ForegroundColor White
} else {
    Write-Host "✗ $errors test(s) failed" -ForegroundColor Red
}

Write-Host ""
