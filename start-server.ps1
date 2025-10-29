# Smart Attendance - Server Startup Script
# This script properly sets PYTHONPATH and starts the server

Write-Host "Starting Smart Attendance Server..." -ForegroundColor Green
Write-Host ""

# Set PYTHONPATH to include src directory
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"

# Check if virtual environment is activated
if (-not (Test-Path "venv\Scripts\hypercorn.exe")) {
    Write-Host "ERROR: Virtual environment not found or hypercorn not installed" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Start server
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Cyan
Write-Host "Starting hypercorn..." -ForegroundColor Cyan
Write-Host ""

& .\venv\Scripts\hypercorn.exe app.main:app --bind 0.0.0.0:8000 --workers 1 --log-level info
