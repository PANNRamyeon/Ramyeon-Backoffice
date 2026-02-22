# Production startup script for PANN Back Office (Windows)

# Configuration
$WORKERS = if ($env:WORKERS) { $env:WORKERS } else { 4 }
$TIMEOUT = if ($env:TIMEOUT) { $env:TIMEOUT } else { 120 }
$PORT = if ($env:PORT) { $env:PORT } else { 8000 }
$BIND = "0.0.0.0:$PORT"

Write-Host "Starting PANN Back Office in Production Mode..." -ForegroundColor Green
Write-Host "Workers: $WORKERS"
Write-Host "Timeout: $TIMEOUT seconds"
Write-Host "Binding to: $BIND"
Write-Host ""

# Activate virtual environment
& .\.venv\Scripts\Activate.ps1

# Start gunicorn with optimal settings
gunicorn config.wsgi:application `
    --workers $WORKERS `
    --timeout $TIMEOUT `
    --bind $BIND `
    --preload `
    --worker-class sync `
    --max-requests 1000 `
    --max-requests-jitter 50 `
    --access-logfile - `
    --error-logfile - `
    --log-level info
