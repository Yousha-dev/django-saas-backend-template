# settings/staging.py
"""
Staging settings - for pre-production testing environment.

Mirrors production but with debug capabilities enabled for troubleshooting.
These settings are used when DJANGO_ENV=staging.
"""

import os

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

ENVIRONMENT = "staging"
DEBUG = True  # Enable debug for staging troubleshooting

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

# More permissive CORS for staging testing
cors_settings = get_cors_settings(debug=True)
for key, value in cors_settings.items():
    locals()[key] = value

# Use production security settings (HTTPS, etc.)
security_settings = get_security_settings(debug=False)
for key, value in security_settings.items():
    locals()[key] = value

ALLOWED_HOSTS = get_allowed_hosts(debug=False)

# Add staging-specific domains
# ALLOWED_HOSTS += ['staging.yourdomain.com', 'staging.duedoom.com']

# =============================================================================
# EMAIL
# =============================================================================

email_settings = get_email_settings()
for key, value in email_settings.items():
    locals()[key] = value

# Console backend for staging (or use SMTP for testing emails)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# =============================================================================
# STRIPE
# =============================================================================

stripe_settings = get_stripe_settings()
for key, value in stripe_settings.items():
    locals()[key] = value

# =============================================================================
# STAGING SPECIFIC SETTINGS
# =============================================================================

# Verbose logging for debugging
LOGGING["loggers"]["django"]["level"] = "INFO"
LOGGING["loggers"]["myapp"]["level"] = "DEBUG"

# Add Sentry for error tracking if configured (same as production)
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
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.5")),
        send_default_pii=False,
        environment="staging",
    )
