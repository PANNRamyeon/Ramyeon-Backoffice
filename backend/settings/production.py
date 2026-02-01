from .base import *
from decouple import config

# Production settings
DEBUG = False

# Allowed hosts - Render auto-assigns URLs
ALLOWED_HOSTS = [
    config('RENDER_EXTERNAL_HOSTNAME', default=''),  # Render provides this automatically
    'localhost',  # For local testing with production settings
    '127.0.0.1',
]

# Add any custom domains you might have
CUSTOM_DOMAINS = config('CUSTOM_DOMAINS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()])
ALLOWED_HOSTS.extend(CUSTOM_DOMAINS)

# Optionally read ALLOWED_HOSTS from env (comma-separated). If provided, merge with above
ENV_ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=lambda v: [s.strip() for s in v.split(',') if s.strip()])
if ENV_ALLOWED_HOSTS:
    ALLOWED_HOSTS = [h for h in (ALLOWED_HOSTS + ENV_ALLOWED_HOSTS) if h]

# CORS settings for production
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# If no specific origins are configured, allow all origins (for flexibility)
# Set CORS_ALLOWED_ORIGINS environment variable to restrict to specific domains
if not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True

# CSRF trusted origins (comma-separated) for HTTPS domains
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# Database Configuration - Always use SQLite for Django ORM
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# The application's custom services will use the DynamoDB connection 
# from app/database.py, which is configured via environment variables.

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []

# SSL settings (Render provides HTTPS automatically)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Email configuration for production (SendGrid integration)
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.sendgrid.net')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='apikey')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@pannpos.com')

# Cache configuration for production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Additional production optimizations
CONN_MAX_AGE = 60  # Database connection pooling

# Render-specific settings
if config('RENDER', default=False, cast=bool):
    # Render automatically provides these
    ALLOWED_HOSTS.append(config('RENDER_EXTERNAL_HOSTNAME', default=''))
    
    # Disable SSL redirect if Render is handling it
    SECURE_SSL_REDIRECT = False