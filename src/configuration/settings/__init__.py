# settings/__init__.py
"""
Settings package - initializes the appropriate settings module based on environment.

The environment is determined by the DJANGO_ENV environment variable:
- development / dev / not set: Uses development.py (SQLite, console email, debug on)
- production / prod: Uses production.py (PostgreSQL, SMTP email, security hardening)
- staging: Uses staging.py (Like production but with debug for troubleshooting)
- test / testing: Uses test.py (In-memory SQLite, optimized for speed)

Usage:
    export DJANGO_ENV=production  # Or set in .env file
    python manage.py runserver

Docker:
    docker-compose -f docker-compose.prod.yml up  # Sets DJANGO_ENV=production
"""

import os
import sys

# Get environment from DJANGO_ENV variable
# Default to 'development' for safety
_environment = os.environ.get("DJANGO_ENV", "development").lower()

# Normalize environment names
ENVIRONMENT_MAP = {
    "production": "production",
    "prod": "production",
    "staging": "staging",
    "stage": "staging",
    "test": "test",
    "testing": "test",
    "development": "development",
    "dev": "development",
    "local": "development",
}

# Determine which settings module to use
environment = ENVIRONMENT_MAP.get(_environment, "development")

# Show which environment is being loaded (skip the reloader child process to avoid duplicate)
if not os.environ.get("RUN_MAIN"):
    if environment == "development":
        print("[Django] Using DEVELOPMENT settings", file=sys.stderr)
    else:
        print(f"[Django] Using {environment.upper()} settings", file=sys.stderr)

# Import the appropriate settings module
# This is the standard Django pattern for environment-specific settings
if environment == "production":
    from .production import *  # noqa: F403
elif environment == "staging":
    from .staging import *  # noqa: F403
elif environment == "test":
    from .test import *  # noqa: F403
else:
    from .development import *  # noqa: F403

# Expose the current environment for use in code
CURRENT_ENVIRONMENT = environment
