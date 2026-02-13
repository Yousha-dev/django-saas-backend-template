# settings/test.py
"""
Test settings - optimized for running tests.

These settings are used when DJANGO_ENV=test or DJANGO_ENV=testing.
Focus is on speed and isolation from external services.
"""

from .base import *
from .components import get_cors_settings, get_security_settings

# =============================================================================
# ENVIRONMENT
# =============================================================================

ENVIRONMENT = "test"
DEBUG = True
TEST = True
USE_STRUCTURED_LOGGING = False

# =============================================================================
# DATABASE - In-memory SQLite for speed
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "ATOMIC_REQUESTS": True,  # Each test in a transaction
    }
}

# =============================================================================
# CACHE - Local memory cache
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# =============================================================================
# CELERY - Run tasks synchronously
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# EMAIL - In-memory backend
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# =============================================================================
# CORS - Permissive
# =============================================================================

cors_settings = get_cors_settings(debug=True)
for key, value in cors_settings.items():
    locals()[key] = value

# =============================================================================
# SECURITY - Relaxed for tests
# =============================================================================

security_settings = get_security_settings(debug=True)
for key, value in security_settings.items():
    locals()[key] = value

ALLOWED_HOSTS = ["*"]

# =============================================================================
# PASSWORD VALIDATORS - Disabled for speed
# =============================================================================

AUTH_PASSWORD_VALIDATORS = []


# =============================================================================
# STRIPE - Disabled
# =============================================================================

STRIPE_ENABLED = False

# =============================================================================
# CHANNEL LAYERS - In-memory
# =============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# =============================================================================
# TEST OPTIMIZATIONS
# =============================================================================

# Use faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Optional: Disable migrations for faster tests
# Uncomment only if you understand the implications
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()

# Empty internal IPs
INTERNAL_IPS = []
