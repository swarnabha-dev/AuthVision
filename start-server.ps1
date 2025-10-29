# Smart Attendance - Production Server
# This script starts the server in production mode

Write-Host "Starting Smart Attendance Server (Production Mode)" -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found" -ForegroundColor Red
    Write-Host "Run: .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting production server..." -ForegroundColor Cyan
Write-Host ""

# Use Python launcher script (handles imports correctly)
& .\venv\Scripts\python.exe run_server.py
