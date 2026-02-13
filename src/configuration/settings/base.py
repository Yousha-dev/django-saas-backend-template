# settings/base.py
"""
Base Django settings - shared across all environments.

This file contains core settings that are common to all environments.
Environment-specific settings are loaded from development.py, production.py, etc.
"""

import contextlib
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
# This should be called before any settings that reference environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"


# =============================================================================
# ENVIRONMENT DETECTION
# =============================================================================

DJANGO_ENV = os.environ.get("DJANGO_ENV", "development").lower()
IS_PRODUCTION = DJANGO_ENV in ("production", "prod")
IS_STAGING = DJANGO_ENV in ("staging",)
IS_TEST = DJANGO_ENV in ("test", "testing")
IS_DEVELOPMENT = not (IS_PRODUCTION or IS_STAGING or IS_TEST)


# =============================================================================
# REQUIRED SETTINGS VALIDATION
# =============================================================================


def _validate_required_settings():
    """
    Validate that required environment variables are set.
    Raises ImproperlyConfigured if any required setting is missing.
    """
    from django.core.exceptions import ImproperlyConfigured

    required_vars = []

    # Check SECRET_KEY in production
    if IS_PRODUCTION and (
        not os.environ.get("SECRET_KEY") or os.environ.get("SECRET_KEY") == "change-me"
    ):
        required_vars.append("SECRET_KEY")

    # Check database settings in production
    if IS_PRODUCTION:
        for var in ["DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST"]:
            if not os.environ.get(var):
                required_vars.append(var)

    if required_vars:
        raise ImproperlyConfigured(
            f"The following required environment variables are missing: {', '.join(required_vars)}"
        )


# =============================================================================
# CORE DJANGO SETTINGS
# =============================================================================

# SECRET_KEY
# In production, this must be set from environment variable
# For development, a fallback is provided
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-key-change-in-production"
)

# DEBUG mode - set in environment-specific files
DEBUG = False

# ALLOWED HOSTS - base set, extended in environment files
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# Site ID for sites framework
SITE_ID = 1

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "myapp.User"

# Remove trailing slashes from URLs
APPEND_SLASH = False


# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "channels",
    "channels_redis",
    "django_celery_results",
    "django_celery_beat",
    "django_extensions",
    "drf_yasg",
]

LOCAL_APPS = [
    "configuration",
    "myapp",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware - structured logging should be early
    "myapp.middleware.RequestLoggingMiddleware",
    # Custom authentication and rate limiting middleware
    # "myapp.middleware.AddCustomFieldsToHeadersMiddleware",  # Not implemented yet
    # "myapp.middleware.AuthenticateUserMiddleware",  # Not implemented yet
    # "myapp.middleware.UserMiddleware",  # Not implemented yet
    "myapp.middleware.APIRateLimitMiddleware",
    # Language preference middleware (after auth)
    "myapp.middleware.LanguageMiddleware",
]

# Optional: Use StructlogMiddleware for automatic context binding
# Set to True in production for structured JSON logs
USE_STRUCTLOG_MIDDLEWARE = (
    os.environ.get("USE_STRUCTLOG_MIDDLEWARE", "true").lower() == "true"
)

if USE_STRUCTLOG_MIDDLEWARE:
    # Insert StructlogMiddleware at the beginning for request context
    with contextlib.suppress(ImportError, AttributeError):
        MIDDLEWARE.insert(0, "myapputils.logging.StructlogMiddleware")


# =============================================================================
# URL CONFIGURATION
# =============================================================================

ROOT_URLCONF = "configuration.urls"

WSGI_APPLICATION = "configuration.wsgi.application"
ASGI_APPLICATION = "configuration.asgi.application"


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    # Add more languages here as needed, e.g.:
    # ('fr', 'French'),
    # ('de', 'German'),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]


# =============================================================================
# STATIC AND MEDIA FILES
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Structured logging configuration
# The actual logging is configured via myapputils.logging.configure_logging()
# This is called in the apps.py ready() method
USE_STRUCTURED_LOGGING = (
    os.environ.get("USE_STRUCTURED_LOGGING", "true").lower() == "true"
)

# Base logging configuration (fallback if structured logging is disabled)
LOGGING_CONFIG = None

# Structlog configuration - imported but not applied until apps.ready()

# Structured logging configuration
from myapp.utils.logging_utils import configure_logging  # noqa: E402

configure_logging(log_level=LOG_LEVEL, json_logs=USE_STRUCTURED_LOGGING)


# =============================================================================
# REST FRAMEWORK CONFIGURATION
# =============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "myapp.authentication.CustomJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    },
    # "EXCEPTION_HANDLER": "myapp.exceptions.custom_exception_handler",  # Not implemented yet
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}


# =============================================================================
# JWT SETTINGS
# =============================================================================


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_CLAIM": "user_id",
    "USER_ROLE_CLAIM": "role",
}

# Swagger/OpenAPI settings
SWAGGER_SETTINGS = {
    "SCHEME": ["https", "http"],
    "SERVERS": [
        {
            "url": os.environ.get("FRONTEND_URL", "http://localhost:3000"),
            "description": "Frontend Application",
        },
        {"url": "http://localhost:8000", "description": "Local Development"},
        {"url": "http://127.0.0.1:8000", "description": "Local Alternative"},
    ],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"',
        }
    },
    "USE_SESSION_AUTH": False,
}


# =============================================================================
# CORS SETTINGS (BASE)
# =============================================================================

# CORS settings are extended in environment-specific files
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]


# =============================================================================
# CSRF SETTINGS (BASE)
# =============================================================================

CSRF_COOKIE_NAME = "csrftoken"
CSRF_HEADER_NAME = "HTTP_X_CSRFTOKEN"


# =============================================================================
# CHANNELS (WEBSOCKET) SETTINGS
# =============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}


# =============================================================================
# CELERY SETTINGS
# =============================================================================

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes

CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


# =============================================================================
# CACHE SETTINGS (DEFAULT)
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}


# =============================================================================
# EMAIL SETTINGS (DEFAULT)
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@example.com")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", "server@example.com")
ADMINS = [
    (name, email)
    for name, email in [
        admin.split(":", 1)
        for admin in os.environ.get("ADMINS", "").split(",")
        if admin
    ]
]


# =============================================================================
# SECURITY SETTINGS (BASE - OVERRIDDEN IN ENV FILES)
# =============================================================================

SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
X_FRAME_OPTIONS = "SAMEORIGIN"

SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"


# =============================================================================
# STRIPE SETTINGS
# =============================================================================

STRIPE_ENABLED = os.environ.get("STRIPE_ENABLED", "false").lower() == "true"
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


# =============================================================================
# PAYPAL SETTINGS
# =============================================================================

PAYPAL_ENABLED = os.environ.get("PAYPAL_ENABLED", "false").lower() == "true"
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
PAYPAL_MODE = os.environ.get("PAYPAL_MODE", "sandbox")  # sandbox or live


# =============================================================================
# NOTIFICATION PROVIDER SETTINGS
# =============================================================================

# SendGrid (Email)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

# Twilio (SMS)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")

# Firebase Cloud Messaging (Push)
FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")


# =============================================================================
# CONTENT MODERATION SETTINGS
# =============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
AZURE_CONTENT_SAFETY_ENDPOINT = os.environ.get("AZURE_CONTENT_SAFETY_ENDPOINT", "")
AZURE_CONTENT_SAFETY_KEY = os.environ.get("AZURE_CONTENT_SAFETY_KEY", "")
MODERATION_STRICT_MODE = (
    os.environ.get("MODERATION_STRICT_MODE", "false").lower() == "true"
)
BANNED_WORDS = (
    os.environ.get("BANNED_WORDS", "").split(",")
    if os.environ.get("BANNED_WORDS")
    else []
)
BANNED_PHRASES = (
    os.environ.get("BANNED_PHRASES", "").split(",")
    if os.environ.get("BANNED_PHRASES")
    else []
)


# =============================================================================
# PAYMENT DEFAULTS
# =============================================================================

DEFAULT_PAYMENT_PROVIDER = os.environ.get("DEFAULT_PAYMENT_PROVIDER", "stripe")


# =============================================================================
# APPLICATION-SPECIFIC SETTINGS
# =============================================================================

# Frontend URL for password reset links and email templates
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Support email
SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@example.com")


# =============================================================================
# SWAGGER SETTINGS (Additional)
# =============================================================================

SWAGGER_SETTINGS.update(
    {
        "JSON_EDITOR": True,
        "SUPPORTED_SUBMIT_METHODS": ["get", "post", "put", "delete", "patch"],
        "OPERATIONS_SORTER": "alpha",
        "TAGS_SORTER": "alpha",
    }
)

REDOC_SETTINGS = {
    "LAZY_RENDERING": False,
}


# =============================================================================
# DEVELOPMENT SETTINGS
# =============================================================================

if IS_DEVELOPMENT:
    # Add internal IPs for debug toolbar
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

    # Enable debug toolbar if installed
    try:
        import debug_toolbar  # noqa: F401

        if "debug_toolbar" not in INSTALLED_APPS:
            INSTALLED_APPS.append("debug_toolbar")
        if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
            MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    except ImportError:
        pass


# =============================================================================
# SETTINGS VALIDATION
# =============================================================================


# Validate settings after all are defined
# This will be called by Django's check framework
def check_settings(**kwargs):
    """Run custom settings validation."""
    from django.core.checks import Warning

    errors = []

    if IS_PRODUCTION and DEBUG:
        errors.append(
            Warning(
                "DEBUG is enabled in production.",
                hint="Set DEBUG=False in production.",
                obj="settings",
                id="settings.W001",
            )
        )

    if (
        IS_PRODUCTION and not SECRET_KEY
    ) or SECRET_KEY == "django-insecure-dev-key-change-in-production":  # noqa: S105
        errors.append(
            Warning(
                "SECRET_KEY is not properly configured for production.",
                hint="Set a secure SECRET_KEY environment variable.",
                obj="settings",
                id="settings.W002",
            )
        )

    return errors
