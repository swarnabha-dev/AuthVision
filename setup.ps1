# Smart Attendance - Setup Script for Windows PowerShell
# Run this script to set up the development environment

Write-Host "Smart Attendance System - Setup" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

# Step 1: Create virtual environment
Write-Host "[1/5] Creating virtual environment..." -ForegroundColor Cyan
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    Write-Host "Please ensure Python 3.12.8 is installed" -ForegroundColor Yellow
    exit 1
}

# Step 2: Activate virtual environment
Write-Host "[2/5] Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

# Step 3: Upgrade pip
Write-Host "[3/5] Upgrading pip..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install --upgrade pip

# Step 4: Install dependencies
Write-Host "[4/5] Installing dependencies..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Step 5: Verify installation
Write-Host "[5/5] Verifying installation..." -ForegroundColor Cyan
.\venv\Scripts\python.exe -c "import fastapi; import pydantic; print('OK: Core dependencies installed')"

Write-Host ""
Write-Host "Setup complete! Next steps:" -ForegroundColor Green
Write-Host "  1. Copy .env.example to .env and configure (optional)" -ForegroundColor White
Write-Host "  2. Run tests: pytest tests\unit\test_routes.py -v" -ForegroundColor White
Write-Host "  3. Start server: .\start-dev.ps1" -ForegroundColor White
Write-Host "  4. Visit: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
