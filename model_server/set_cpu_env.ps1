# CPU Optimization Environment Variables for TensorFlow & PyTorch
# Run this script before starting the model server for optimal CPU performance

Write-Host "Setting CPU optimization environment variables..." -ForegroundColor Cyan

# Disable GPU entirely (faster startup, no CUDA search)
$env:CUDA_VISIBLE_DEVICES = "-1"
Write-Host "✓ CUDA_VISIBLE_DEVICES = -1 (GPU disabled)" -ForegroundColor Green

# Enable Intel oneDNN/MKL-DNN optimizations (enabled by default in TF 2.16+)
$env:TF_ENABLE_ONEDNN_OPTS = "1"
Write-Host "✓ TF_ENABLE_ONEDNN_OPTS = 1 (Intel MKL enabled)" -ForegroundColor Green

# Set number of threads (adjust based on your CPU cores)
# For 4-core CPU: use 4 intra-op threads
# For 8-core CPU: use 6-8 intra-op threads
$cores = (Get-WmiObject -Class Win32_Processor | Select-Object -ExpandProperty NumberOfCores)
$threads = [Math]::Max(2, $cores - 1)

$env:OMP_NUM_THREADS = "$threads"
Write-Host "✓ OMP_NUM_THREADS = $threads" -ForegroundColor Green

$env:TF_NUM_INTRAOP_THREADS = "$threads"
Write-Host "✓ TF_NUM_INTRAOP_THREADS = $threads" -ForegroundColor Green

$env:TF_NUM_INTEROP_THREADS = "2"
Write-Host "✓ TF_NUM_INTEROP_THREADS = 2" -ForegroundColor Green

# Intel MKL settings for CPU optimization
$env:KMP_BLOCKTIME = "0"
Write-Host "✓ KMP_BLOCKTIME = 0 (no thread spin)" -ForegroundColor Green

$env:KMP_AFFINITY = "granularity=fine,compact,1,0"
Write-Host "✓ KMP_AFFINITY = granularity=fine,compact,1,0" -ForegroundColor Green

Write-Host "`nCPU optimization environment variables set successfully!" -ForegroundColor Yellow
Write-Host "Detected CPU cores: $cores" -ForegroundColor Cyan
Write-Host "Using $threads threads for parallel operations" -ForegroundColor Cyan
Write-Host "`nYou can now start the model server with:" -ForegroundColor White
Write-Host "  hypercorn app.main:app --bind 0.0.0.0:8001 --reload" -ForegroundColor Gray
