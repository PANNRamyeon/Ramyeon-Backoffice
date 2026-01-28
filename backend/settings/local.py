from .base import *
from decouple import config

# Development settings
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS settings for development (your frontend runs on 5173)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # Alternative port
    "http://127.0.0.1:3000",
]

# Allow all origins in development for easier testing
CORS_ALLOW_ALL_ORIGINS = True

# Database configuration for development
# The default Django database is set to SQLite for auth, sessions, etc.
# Application data models use PynamoDB, which connects to DynamoDB
# using credentials from the .env file (see dynamo_base.py).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Development-specific middleware (add any debug middleware here)
if DEBUG:
    # Add debug toolbar if you want (uncomment if you install it)
    # INSTALLED_APPS += ['debug_toolbar']
    # MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    pass

# Email backend for development (console output)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Development logging - Inherits from base.py and overrides levels
# Set root and Django loggers to DEBUG for more verbose output.
LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'INFO'

# Silence the overly verbose AWS SDK (boto3/botocore) logs
LOGGING['loggers']['boto3'] = {'level': 'WARNING'}
LOGGING['loggers']['botocore'] = {'level': 'WARNING'}

# Disable some security features in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
