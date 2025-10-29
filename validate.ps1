# Smart Attendance - Validation Script
# Run this to validate Module 1 implementation

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Smart Attendance - Module 1 Validation" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$errors = 0

# Check 1: Virtual environment exists
Write-Host "[1/6] Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "  ✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "  ✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "    Run: python -m venv venv" -ForegroundColor Yellow
    $errors++
}

# Check 2: Dependencies installed
Write-Host "[2/6] Checking dependencies..." -ForegroundColor Yellow
try {
    $output = & .\venv\Scripts\python.exe -c "import fastapi; import pydantic; print('OK')" 2>&1
    if ($output -match "OK") {
        Write-Host "  ✓ Core dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Dependencies not installed" -ForegroundColor Red
        Write-Host "    Run: pip install -r requirements.txt" -ForegroundColor Yellow
        $errors++
    }
} catch {
    Write-Host "  ✗ Error checking dependencies" -ForegroundColor Red
    $errors++
}

# Check 3: .env file exists
Write-Host "[3/6] Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  ✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env file not found (optional for testing)" -ForegroundColor Yellow
    Write-Host "    Run: Copy-Item .env.example .env" -ForegroundColor Cyan
}

# Check 4: Import test
Write-Host "[4/6] Testing imports..." -ForegroundColor Yellow
try {
    $output = & .\venv\Scripts\python.exe -c "from app.main import app; print('OK')" 2>&1
    if ($output -match "OK") {
        Write-Host "  ✓ Application imports successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Import errors detected" -ForegroundColor Red
        Write-Host $output
        $errors++
    }
} catch {
    Write-Host "  ✗ Error testing imports" -ForegroundColor Red
    $errors++
}

# Check 5: Run unit tests
Write-Host "[5/6] Running unit tests..." -ForegroundColor Yellow
try {
    $testOutput = & .\venv\Scripts\python.exe -m pytest tests/unit/test_routes.py -v --tb=short 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ All unit tests passed" -ForegroundColor Green
        # Count tests
        $testCount = ($testOutput | Select-String "passed").Matches.Count
        if ($testCount -gt 0) {
            Write-Host "    Tests executed successfully" -ForegroundColor Green
        }
    } else {
        Write-Host "  ✗ Unit tests failed" -ForegroundColor Red
        Write-Host $testOutput
        $errors++
    }
} catch {
    Write-Host "  ✗ Error running tests" -ForegroundColor Red
    Write-Host "    Ensure pytest is installed" -ForegroundColor Yellow
    $errors++
}

# Check 6: Server can start (quick test)
Write-Host "[6/6] Testing server startup..." -ForegroundColor Yellow
try {
    $job = Start-Job -ScriptBlock {
        param($pythonPath)
        & $pythonPath -c "from app.main import app; print('SERVER_OK')"
    } -ArgumentList (Resolve-Path ".\venv\Scripts\python.exe")
    
    Wait-Job $job -Timeout 5 | Out-Null
    $output = Receive-Job $job
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue
    
    if ($output -match "SERVER_OK") {
        Write-Host "  ✓ Server can initialize" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Could not verify server startup" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Could not test server startup" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if ($errors -eq 0) {
    Write-Host ""
    Write-Host "✓ All checks passed! Module 1 is ready." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start server: .\venv\Scripts\hypercorn.exe src.app.main:app --bind 0.0.0.0:8000" -ForegroundColor White
    Write-Host "  2. Visit: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  3. Test endpoints via interactive docs" -ForegroundColor White
    Write-Host "  4. Confirm with agent: 'Module 1 validated, proceed to Module 2'" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ $errors error(s) found. Please fix before proceeding." -ForegroundColor Red
    Write-Host ""
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  - Run: .\setup.ps1" -ForegroundColor White
    Write-Host "  - Or manually: pip install -r requirements.txt" -ForegroundColor White
    Write-Host ""
}

Write-Host "For detailed validation steps, see: VALIDATION_CHECKLIST.md" -ForegroundColor Cyan
Write-Host ""
