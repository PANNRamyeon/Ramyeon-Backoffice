# Production Deployment Guide - PANN Back Office

## Optimizations Implemented

### 1. Singleton CategoryService Pattern
**Problem:** CategoryService was being instantiated on every request, causing repeated database checks.

**Solution:** 
- Added module-level singleton pattern with `get_category_service()`
- Added class-level flag to run `ensure_uncategorized_category_exists()` only once per server lifetime
- All views now use the singleton instance

**Impact:** Eliminates repeated initialization overhead on every request.

### 2. Lazy Import Fix
**Problem:** Circular imports caused slow initialization.

**Solution:** Implemented lazy loading in `app/services/__init__.py`

**Impact:** Reduces cold start time.

### 3. Production WSGI Server
**Problem:** Django's development server is not optimized for production.

**Solution:** Use gunicorn with pre-forking and preloading.

**Impact:** 
- Multiple worker processes
- No cold starts after deployment
- Better performance under load

---

## Development Usage

### Current Setup (Already Working)
```bash
cd backend
python manage.py runserver
```

**Expected Behavior:**
- First request to each endpoint: ~1-2s (warm-up)
- Subsequent requests: ~0.5-1s

---

## Production Deployment

### Step 1: Install Production Requirements
```bash
cd backend
pip install -r requirements-prod.txt
```

### Step 2: Configure Environment Variables
```bash
# Set in your .env or system environment
WORKERS=4              # Number of gunicorn workers (2 x CPU cores recommended)
TIMEOUT=120            # Request timeout in seconds
PORT=8000             # Port to bind to
```

### Step 3: Start Production Server

**Linux/Mac:**
```bash
chmod +x start_production.sh
./start_production.sh
```

**Windows (PowerShell):**
```powershell
.\start_production.ps1
```

**Manual (any OS):**
```bash
gunicorn config.wsgi:application \
    --workers 4 \
    --timeout 120 \
    --bind 0.0.0.0:8000 \
    --preload \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
```

### Step 4: Warm-up Server (Eliminate Cold Starts)

After deployment, run the warm-up script to hit all endpoints:

```bash
# Without authentication (public endpoints only)
python warmup_server.py

# With authentication (all endpoints)
WARMUP_TOKEN="your_admin_jwt_token" python warmup_server.py
```

**What it does:**
- Hits all major endpoints sequentially
- Forces initialization of all code paths
- Eliminates first-request delays
- Verifies all endpoints are responding

---

## Production Configuration Explained

### Gunicorn Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `--workers 4` | 4 workers | Handle concurrent requests (2 x CPU cores) |
| `--timeout 120` | 2 minutes | Max request processing time |
| `--preload` | Enabled | Load code before forking (eliminates cold starts) |
| `--max-requests 1000` | 1000 | Restart worker after N requests (prevents memory leaks) |
| `--max-requests-jitter 50` | 50 | Randomize restart (prevent all workers restarting at once) |
| `--worker-class sync` | Sync | Standard worker (good for CPU-bound tasks) |

### Worker Count Recommendation
- **2 CPU cores**: 4 workers
- **4 CPU cores**: 8 workers
- **8 CPU cores**: 16 workers
- Formula: `(2 x CPU cores) + 1`

---

## Monitoring & Health Checks

### Health Check Endpoint
```bash
curl http://localhost:8000/api/v1/admin/users/health/
```

### Check Worker Status
```bash
# View gunicorn processes
ps aux | grep gunicorn

# View logs
tail -f /var/log/gunicorn/access.log
tail -f /var/log/gunicorn/error.log
```

---

## Performance Benchmarks

### Before Optimization
- First request to endpoint: 38 seconds
- Subsequent requests: 1 second
- CategoryService instantiated on every request

### After Optimization (Development)
- First request to endpoint: ~1-2 seconds
- Subsequent requests: ~0.5-1 second
- CategoryService instantiated once

### After Optimization (Production with Warm-up)
- All requests: ~0.5-1 second
- No cold starts
- Better concurrency

---

## Deployment Checklist

- [ ] Install production requirements (`requirements-prod.txt`)
- [ ] Set environment variables (WORKERS, TIMEOUT, PORT)
- [ ] Update `.env` with production settings
- [ ] Run database migrations if needed
- [ ] Start gunicorn with `--preload`
- [ ] Run warm-up script after deployment
- [ ] Set up health check monitoring
- [ ] Configure reverse proxy (nginx/Apache) if needed
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules

---

## Troubleshooting

### Issue: Workers timing out
**Solution:** Increase `--timeout` value (default 120s)

### Issue: High memory usage
**Solution:** Reduce `--max-requests` to restart workers more frequently

### Issue: Slow first request after restart
**Solution:** Run `warmup_server.py` after deployment

### Issue: 502 Bad Gateway
**Solution:** Check gunicorn is running and binding to correct port

---

## Rollback Plan

If issues occur in production:

1. **Stop gunicorn:**
   ```bash
   pkill gunicorn
   ```

2. **Revert to development server temporarily:**
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

3. **Investigate logs and fix issues**

4. **Redeploy with fixes**

---

## Additional Optimizations (Future)

- [ ] Add Redis caching for frequently accessed data
- [ ] Implement database connection pooling
- [ ] Add APM (Application Performance Monitoring)
- [ ] Configure CDN for static assets
- [ ] Implement rate limiting
- [ ] Add request/response compression
- [ ] Set up load balancing for multiple servers

---

## Support

For issues or questions, check:
- Application logs
- Gunicorn logs
- DynamoDB CloudWatch metrics
- Server resource usage (CPU, RAM, disk)
