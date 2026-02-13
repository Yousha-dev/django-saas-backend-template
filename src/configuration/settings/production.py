# settings/production.py
"""
Production settings - optimized for security and performance.

These settings are used when DJANGO_ENV=production or DJANGO_ENV=prod.

IMPORTANT: Before deploying to production, ensure:
1. SECRET_KEY is set to a strong random value
2. Database credentials are configured
3. ALLOWED_HOSTS includes your production domain(s)
4. CORS_ALLOWED_ORIGINS includes your frontend domain(s)
5. Email backend is properly configured
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

ENVIRONMENT = "production"
DEBUG = False

# =============================================================================
# REQUIRED SETTINGS VALIDATION
# =============================================================================

# Validate that required settings are present for production
_validate_required_settings()

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = get_database_settings()

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

cors_settings = get_cors_settings(debug=False)
for key, value in cors_settings.items():
    locals()[key] = value

security_settings = get_security_settings(debug=False)
for key, value in security_settings.items():
    locals()[key] = value

ALLOWED_HOSTS = get_allowed_hosts(debug=False)

# =============================================================================
# EMAIL
# =============================================================================

email_settings = get_email_settings()
for key, value in email_settings.items():
    locals()[key] = value

# SMTP backend for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# =============================================================================
# STRIPE
# =============================================================================

stripe_settings = get_stripe_settings()
for key, value in stripe_settings.items():
    locals()[key] = value

# =============================================================================
# PRODUCTION SPECIFIC SETTINGS
# =============================================================================

# Secure proxy SSL header for reverse proxy (nginx, AWS ELB, etc.)
# Already set in security_settings, but ensuring it's explicit
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Production logging - less verbose, focused on errors
LOGGING["loggers"]["django"]["level"] = "WARNING"
LOGGING["loggers"]["myapp"]["level"] = "INFO"

# Add Sentry for error tracking if configured
if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
        environment="production",
    )

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================

# Connection pooling
CONN_MAX_AGE = 60

# Static files storage - consider using S3 or similar in production
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
