# settings/development.py
"""
Development settings - optimized for local development.

These settings are used when DJANGO_ENV=development or when not specified.
"""

from .base import *
from .components import (
    get_allowed_hosts,
    get_cache_settings,
    get_celery_settings,
    get_channel_layers_settings,
    get_cors_settings,
    get_database_settings,
    get_email_settings,
    get_redis_settings,
    get_security_settings,
    get_stripe_settings,
)

# =============================================================================
# ENVIRONMENT
# =============================================================================

ENVIRONMENT = "development"
DEBUG = True

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = get_database_settings()

# For local development without Docker/PostgreSQL, SQLite is used by default
# Set USE_SQLITE=false in .env to use PostgreSQL

# =============================================================================
# REDIS / CACHE / CHANNELS
# =============================================================================

redis_config = get_redis_settings()
CACHES = get_cache_settings(redis_config["url"])
CHANNEL_LAYERS = get_channel_layers_settings(redis_config["url"])

# =============================================================================
# CELERY
# =============================================================================

celery_settings = get_celery_settings(redis_config["url"])
for key, value in celery_settings.items():
    locals()[key] = value

# =============================================================================
# CORS & SECURITY
# =============================================================================

cors_settings = get_cors_settings(debug=True)
for key, value in cors_settings.items():
    locals()[key] = value

security_settings = get_security_settings(debug=True)
for key, value in security_settings.items():
    locals()[key] = value

ALLOWED_HOSTS = get_allowed_hosts(debug=True)

# =============================================================================
# EMAIL
# =============================================================================

email_settings = get_email_settings()
for key, value in email_settings.items():
    locals()[key] = value

# Console backend for development - emails printed to console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# STRIPE
# =============================================================================

stripe_settings = get_stripe_settings()
for key, value in stripe_settings.items():
    locals()[key] = value

# =============================================================================
# DEVELOPMENT SPECIFIC SETTINGS
# =============================================================================

# Show full error pages
DEBUG_PROPAGATE_EXCEPTIONS = False

# Add internal IPs for debug toolbar
INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Increase rate limits for development testing
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # inherit base settings
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/day",
        "user": "100000/day",
    },
}

# Disable rate limiting in development (optional)
# RATELIMIT_ENABLE = False

# =============================================================================
# DEBUG TOOLBAR
# =============================================================================

try:
    import debug_toolbar  # noqa: F401

    if "debug_toolbar" not in INSTALLED_APPS:
        INSTALLED_APPS.append("debug_toolbar")
    if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
        MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
except ImportError:
    pass
