# settings/components.py
"""
Settings components - reusable setting groups for different concerns.

This module provides factory functions for environment-specific configurations.
Each function returns a dictionary of settings that can be applied to the
Django settings module.

Usage:
    from .components import get_database_settings
    DATABASES = get_database_settings()
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Helper to get boolean environment variable."""
    return os.environ.get(key, str(default)).lower() in ("true", "1", "yes", "on")


def _get_env_int(key: str, default: int = 0) -> int:
    """Helper to get integer environment variable."""
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_env_list(key: str, default: list | None = None) -> list:
    """Helper to get list from comma-separated environment variable."""
    if default is None:
        default = []
    value = os.environ.get(key, "")
    return [item.strip() for item in value.split(",") if item.strip()] or default


# =============================================================================
# DATABASE SETTINGS
# =============================================================================


def get_database_settings() -> dict:
    """
    Returns database configuration based on environment.

    Uses PostgreSQL in production/staging, SQLite for development/testing.

    Environment variables:
        DB_ENGINE: Database backend (default: postgresql)
        DB_NAME: Database name
        DB_USER: Database user
        DB_PASSWORD: Database password
        DB_HOST: Database host
        DB_PORT_NUMBER: Database port
        DOCKER_ENV: Set to 'true' when running in Docker
    """
    is_docker = _get_env_bool("DOCKER_ENV")
    is_test = _get_env_bool("TEST", False)
    use_sqlite = _get_env_bool("USE_SQLITE", is_test)

    if use_sqlite:
        return {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }

    # PostgreSQL configuration
    return {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "template"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("DB_HOST", "db" if is_docker else "localhost"),
            "PORT": _get_env_int("DB_PORT_NUMBER", 5432),
            "OPTIONS": {
                "connect_timeout": 10,
                "sslmode": os.environ.get("DB_SSLMODE", "prefer"),
            },
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
    }


# =============================================================================
# REDIS SETTINGS
# =============================================================================


def get_redis_settings() -> dict:
    """
    Returns Redis connection settings.

    Environment variables:
        REDIS_HOST: Redis host (default: localhost or 'redis' in Docker)
        REDIS_PORT_NUMBER: Redis port (default: 6379)
        REDIS_PASSWORD: Redis password
        REDIS_DB: Redis database number (default: 0)
        DOCKER_ENV: Set to 'true' when running in Docker

    Returns:
        dict with 'url' key containing the Redis connection URL
    """
    is_docker = _get_env_bool("DOCKER_ENV")

    redis_host = os.environ.get("REDIS_HOST", "redis" if is_docker else "localhost")
    redis_port = _get_env_int("REDIS_PORT_NUMBER", 6379)
    redis_password = os.environ.get("REDIS_PASSWORD", "")
    redis_db = _get_env_int("REDIS_DB", 0)

    if redis_password:
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    return {
        "url": redis_url,
        "host": redis_host,
        "port": redis_port,
        "password": redis_password,
        "db": redis_db,
    }


def get_cache_settings(redis_url: str) -> dict:
    """
    Returns Django cache configuration using Redis.

    Args:
        redis_url: Redis connection URL

    Environment variables:
        CACHE_DEFAULT_TIMEOUT: Default cache timeout in seconds (default: 300)
    """
    timeout = _get_env_int("CACHE_DEFAULT_TIMEOUT", 300)
    os.environ.get("REDIS_PASSWORD", "")

    return {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "TIMEOUT": timeout,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PARSER_CLASS": "redis.connection.HiredisParser"
                if os.environ.get("USE_HIREDIS", "false").lower() == "true"
                else "redis.connection.DefaultParser",
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
                "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            },
            "KEY_PREFIX": "template",
            "VERSION": 1,
        },
    }


def get_channel_layers_settings(redis_url: str) -> dict:
    """
    Returns Django Channels layer configuration using Redis.

    Args:
        redis_url: Redis connection URL
    """
    return {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [redis_url],
                "capacity": 1000,
                "expiry": 60,
                "group_expiry": 86400,  # 24 hours
            },
        },
    }


# =============================================================================
# CELERY SETTINGS
# =============================================================================


def get_celery_settings(redis_url: str) -> dict:
    """
    Returns Celery configuration.

    Args:
        redis_url: Redis URL for result backend

    Environment variables:
        CELERY_BROKER_URL: Message broker URL (default: uses RabbitMQ settings)
        RABBITMQ_USER: RabbitMQ user
        RABBITMQ_PASSWORD: RabbitMQ password
        RABBITMQ_HOST: RabbitMQ host
        RABBITMQ_PORT_NUMBER: RabbitMQ port
        CELERY_WORKER_CONCURRENCY: Number of worker processes
        CELERY_TASK_TIME_LIMIT: Task time limit in seconds
    """
    from celery.schedules import crontab

    is_docker = _get_env_bool("DOCKER_ENV")

    # Broker configuration (RabbitMQ or Redis)
    broker_url = os.environ.get(
        "CELERY_BROKER_URL",
        f"amqp://{os.environ.get('RABBITMQ_USER', 'guest')}:"
        f"{os.environ.get('RABBITMQ_PASSWORD', 'guest')}@"
        f"{os.environ.get('RABBITMQ_HOST', 'rabbitmq' if is_docker else 'localhost')}:"
        f"{_get_env_int('RABBITMQ_PORT_NUMBER', 5672)}//",
    )

    return {
        # Broker configuration
        "CELERY_BROKER_URL": broker_url,
        "CELERY_RESULT_BACKEND": f"{redis_url}/2",
        "CELERY_CACHE_BACKEND": f"{redis_url}/3",
        # Serialization
        "CELERY_ACCEPT_CONTENT": ["json"],
        "CELERY_TASK_SERIALIZER": "json",
        "CELERY_RESULT_SERIALIZER": "json",
        "CELERY_RESULT_EXTENDED": True,
        # Timezone
        "CELERY_TIMEZONE": "UTC",
        "CELERY_ENABLE_UTC": True,
        # Task settings
        "CELERY_TASK_TRACK_STARTED": True,
        "CELERY_TASK_TIME_LIMIT": _get_env_int(
            "CELERY_TASK_TIME_LIMIT", 1800
        ),  # 30 min
        "CELERY_TASK_SOFT_TIME_LIMIT": _get_env_int(
            "CELERY_TASK_SOFT_TIME_LIMIT", 1500
        ),  # 25 min
        "CELERY_TASK_IGNORE_RESULT": True,
        "CELERY_TASK_RESULT_EXPIRES": 3600,  # 1 hour
        # Worker settings
        "CELERY_WORKER_CONCURRENCY": _get_env_int("CELERY_WORKER_CONCURRENCY", 4),
        "CELERY_WORKER_MAX_TASKS_PER_CHILD": 1000,
        "CELERY_WORKER_DISABLE_RATE_LIMITS": True,
        "CELERY_WORKER_PREFETCH_MULTIPLIER": 1,
        # Beat scheduler
        "CELERY_BEAT_SCHEDULER": "django_celery_beat.schedulers:DatabaseScheduler",
        "CELERY_BEAT_SCHEDULE": {
            "cleanup-old-logs": {
                "task": "myapp.tasks.tasks.cleanup_old_logs",
                "schedule": crontab(minute=0, hour=2),  # 2 AM daily
            },
        },
        # Task routing
        "CELERY_TASK_ROUTES": {
            "myapp.tasks.tasks.*": {"queue": "default"},
            "myapp.tasks.email_tasks.*": {"queue": "email"},
        },
        # Other settings
        "CELERY_SEND_TASK_ERROR_EMAILS": True,
        "CELERY_SEND_SENT_EVENT": True,
    }


# =============================================================================
# CORS SETTINGS
# =============================================================================


def get_cors_settings(debug: bool = False) -> dict:
    """
    Returns CORS configuration based on debug mode.

    Args:
        debug: Whether debug mode is enabled

    Environment variables:
        CORS_ALLOWED_ORIGINS: Comma-separated list of allowed origins
        CORS_ALLOW_ALL_ORIGINS: Allow all origins (not recommended for production)
    """
    # Base allowed origins from environment
    env_origins = _get_env_list("CORS_ALLOWED_ORIGINS")

    # Development origins
    development_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://localhost:8090",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Production origins - should come from environment
    production_origins = env_origins or [
        # Add your production domains here
        "https://*.template.com",
    ]

    if debug:
        origins = development_origins
        allow_all = _get_env_bool("CORS_ALLOW_ALL_ORIGINS", True)
    else:
        origins = production_origins
        allow_all = _get_env_bool("CORS_ALLOW_ALL_ORIGINS", False)

    return {
        "CORS_ALLOW_ALL_ORIGINS": allow_all,
        "CORS_ALLOWED_ORIGINS": origins,
        "CORS_ALLOW_HEADERS": [
            "accept",
            "accept-encoding",
            "authorization",
            "content-type",
            "dnt",
            "origin",
            "user-agent",
            "x-csrftoken",
            "x-requested-with",
        ],
        "CORS_ALLOW_METHODS": [
            "DELETE",
            "GET",
            "OPTIONS",
            "PATCH",
            "POST",
            "PUT",
        ],
        "CORS_ALLOW_CREDENTIALS": True,
        "CSRF_TRUSTED_ORIGINS": origins,
    }


# =============================================================================
# SECURITY SETTINGS
# =============================================================================


def get_security_settings(debug: bool = False) -> dict:
    """
    Returns security settings based on debug mode.

    Args:
        debug: Whether debug mode is enabled
    """
    if debug:
        return {
            "SECURE_SSL_REDIRECT": False,
            "SECURE_PROXY_SSL_HEADER": None,
            "SESSION_COOKIE_SECURE": False,
            "CSRF_COOKIE_SECURE": False,
            "SECURE_HSTS_SECONDS": 0,
            "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
            "SECURE_HSTS_PRELOAD": False,
            "SECURE_CONTENT_TYPE_NOSNIFF": False,
            "SECURE_BROWSER_XSS_FILTER": False,
            "SECURE_REFERRER_POLICY": "same-origin",
            "X_FRAME_OPTIONS": "SAMEORIGIN",
        }

    return {
        "SECURE_SSL_REDIRECT": True,
        "SECURE_PROXY_SSL_HEADER": ("HTTP_X_FORWARDED_PROTO", "https"),
        "SECURE_HSTS_SECONDS": 31536000,  # 1 year
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
        "SECURE_HSTS_PRELOAD": True,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "CSRF_COOKIE_SECURE": True,
        "CSRF_COOKIE_HTTPONLY": True,
        "CSRF_COOKIE_SAMESITE": "Lax",
        "SECURE_CONTENT_TYPE_NOSNIFF": True,
        "SECURE_BROWSER_XSS_FILTER": True,
        "SECURE_REFERRER_POLICY": "strict-origin-when-cross-origin",
        "X_FRAME_OPTIONS": "DENY",
    }


# =============================================================================
# ALLOWED HOSTS
# =============================================================================


def get_allowed_hosts(debug: bool = False) -> list:
    """
    Returns allowed hosts based on debug mode.

    Args:
        debug: Whether debug mode is enabled

    Environment variables:
        ALLOWED_HOSTS: Comma-separated list of allowed hosts
    """
    env_hosts = _get_env_list("ALLOWED_HOSTS")

    if env_hosts:
        return env_hosts

    if debug:
        return ["*"]

    return [
        "localhost",
        "127.0.0.1",
        # Add your production domains here or via ALLOWED_HOSTS env var
    ]


# =============================================================================
# EMAIL SETTINGS
# =============================================================================


def get_email_settings() -> dict:
    """
    Returns email configuration from environment.

    Environment variables:
        EMAIL_HOST: SMTP host
        EMAIL_PORT: SMTP port
        EMAIL_HOST_USER: SMTP username
        EMAIL_HOST_PASSWORD: SMTP password
        EMAIL_USE_TLS: Use TLS (true/false)
        EMAIL_USE_SSL: Use SSL (true/false)
        DEFAULT_FROM_EMAIL: Default from email address
    """
    return {
        "EMAIL_HOST": os.environ.get("EMAIL_HOST", "localhost"),
        "EMAIL_PORT": _get_env_int("EMAIL_PORT", 587),
        "EMAIL_HOST_USER": os.environ.get("EMAIL_HOST_USER", ""),
        "EMAIL_HOST_PASSWORD": os.environ.get("EMAIL_HOST_PASSWORD", ""),
        "EMAIL_USE_TLS": _get_env_bool("EMAIL_USE_TLS", True),
        "EMAIL_USE_SSL": _get_env_bool("EMAIL_USE_SSL", False),
        "EMAIL_TIMEOUT": _get_env_int("EMAIL_TIMEOUT", 30),
        "DEFAULT_FROM_EMAIL": os.environ.get(
            "DEFAULT_FROM_EMAIL", "noreply@template.com"
        ),
        "SERVER_EMAIL": os.environ.get("SERVER_EMAIL", "server@template.com"),
    }


# =============================================================================
# STRIPE SETTINGS
# =============================================================================


def get_stripe_settings() -> dict:
    """
    Returns Stripe configuration.

    Environment variables:
        STRIPE_ENABLED: Enable Stripe (true/false)
        STRIPE_SECRET_KEY: Stripe secret key
        STRIPE_PUBLISHABLE_KEY: Stripe publishable key
        STRIPE_WEBHOOK_SECRET: Stripe webhook secret
    """
    return {
        "STRIPE_ENABLED": _get_env_bool("STRIPE_ENABLED", False),
        "STRIPE_SECRET_KEY": os.environ.get("STRIPE_SECRET_KEY", ""),
        "STRIPE_PUBLISHABLE_KEY": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        "STRIPE_WEBHOOK_SECRET": os.environ.get("STRIPE_WEBHOOK_SECRET", ""),
        "STRIPE_API_VERSION": os.environ.get("STRIPE_API_VERSION", "2023-10-16"),
    }


# =============================================================================
# LOGGING SETTINGS
# =============================================================================


def get_logging_settings(level: str = "INFO") -> dict:
    """
    Returns logging configuration with the specified level.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {asctime} {module} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "level": level,
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "myapp": {
                "handlers": ["console"],
                "level": "DEBUG" if level == "DEBUG" else "INFO",
                "propagate": False,
            },
        },
    }
