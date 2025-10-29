# Smart Attendance - Development Server (with auto-reload)
# This script starts the server in development mode with hot-reload

Write-Host "Starting Smart Attendance Server (Development Mode)" -ForegroundColor Green
Write-Host "Auto-reload: ENABLED" -ForegroundColor Yellow
Write-Host ""

# Set PYTHONPATH to include src directory
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

# Check if virtual environment is activated
if (-not (Test-Path "venv\Scripts\hypercorn.exe")) {
    Write-Host "ERROR: Virtual environment not found or hypercorn not installed" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Start server with reload
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "Starting hypercorn with auto-reload..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& .\venv\Scripts\hypercorn.exe app.main:app --bind 0.0.0.0:8000 --reload --log-level debug
