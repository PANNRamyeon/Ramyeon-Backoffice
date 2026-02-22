#!/bin/bash
# Production startup script for PANN Back Office

# Configuration
WORKERS=${WORKERS:-4}  # Default 4 workers (2 x CPU cores is recommended)
TIMEOUT=${TIMEOUT:-120}  # 2 minutes timeout
PORT=${PORT:-8000}
BIND=${BIND:-0.0.0.0:$PORT}

echo "Starting PANN Back Office in Production Mode..."
echo "Workers: $WORKERS"
echo "Timeout: $TIMEOUT seconds"
echo "Binding to: $BIND"

# Start gunicorn with optimal settings
gunicorn config.wsgi:application \
    --workers $WORKERS \
    --timeout $TIMEOUT \
    --bind $BIND \
    --preload \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info

# Notes:
# --preload: Load application code before forking workers (eliminates cold starts)
# --max-requests: Restart workers after N requests (prevents memory leaks)
# --max-requests-jitter: Add randomness to prevent all workers restarting at once
