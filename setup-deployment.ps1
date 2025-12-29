# AuthVision Deployment Setup Script
# Run this script on each deployment PC to configure JWT secret

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AuthVision 5G Lab - Deployment Setup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$currentSecret = $env:MAIN_BACKEND_JWT_SECRET

if ($currentSecret) {
    Write-Host "Current JWT_SECRET is set: $($currentSecret.Substring(0, [Math]::Min(10, $currentSecret.Length)))..." -ForegroundColor Yellow
    $choice = Read-Host "Do you want to change it? (y/n)"
    if ($choice -ne 'y') {
        Write-Host "Keeping existing secret." -ForegroundColor Green
        exit
    }
}

Write-Host ""
Write-Host "Choose an option:" -ForegroundColor White
Write-Host "1. Generate a new secure JWT secret (for first deployment)" -ForegroundColor White
Write-Host "2. Enter an existing JWT secret (for multi-PC deployment)" -ForegroundColor White
Write-Host ""

$option = Read-Host "Enter option (1 or 2)"

if ($option -eq "1") {
    # Generate new secret
    Add-Type -AssemblyName System.Security
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::Create()
    $rng.GetBytes($bytes)
    $newSecret = [Convert]::ToBase64String($bytes) -replace '\+','-' -replace '/','_' -replace '=',''
    
    Write-Host ""
    Write-Host "Generated new JWT secret:" -ForegroundColor Green
    Write-Host $newSecret -ForegroundColor Yellow
    Write-Host ""
    Write-Host "IMPORTANT: Save this secret! You'll need it for other PCs." -ForegroundColor Red
    Write-Host ""
    
    $confirm = Read-Host "Set this as JWT_SECRET? (y/n)"
    if ($confirm -eq 'y') {
        $env:MAIN_BACKEND_JWT_SECRET = $newSecret
        [Environment]::SetEnvironmentVariable("MAIN_BACKEND_JWT_SECRET", $newSecret, "User")
        Write-Host "JWT_SECRET set successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Copy this secret for other PCs:" -ForegroundColor Cyan
        Write-Host $newSecret -ForegroundColor Yellow
    }
    
} elseif ($option -eq "2") {
    # Enter existing secret
    Write-Host ""
    Write-Host "Enter the JWT secret from your main deployment PC:" -ForegroundColor Yellow
    $existingSecret = Read-Host "JWT_SECRET"
    
    if ($existingSecret) {
        $env:MAIN_BACKEND_JWT_SECRET = $existingSecret
        [Environment]::SetEnvironmentVariable("MAIN_BACKEND_JWT_SECRET", $existingSecret, "User")
        Write-Host ""
        Write-Host "JWT_SECRET set successfully!" -ForegroundColor Green
        Write-Host "This PC will now be able to validate tokens from other PCs." -ForegroundColor Green
    } else {
        Write-Host "No secret entered. Exiting." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "Invalid option. Exiting." -ForegroundColor Red
    exit
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "1. Start backend: python -m main_backend" -ForegroundColor Gray
Write-Host "2. Start model service: python -m model_service" -ForegroundColor Gray
Write-Host "3. Start frontend: cd Authvision_Frontend; npm run dev" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
