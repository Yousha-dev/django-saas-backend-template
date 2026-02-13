#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    """Run administrative tasks."""
    # Set the default Django settings module
    # To use a specific environment, set the DJANGO_ENV environment variable:
    # - DJANGO_ENV=development (default) - for local development
    # - DJANGO_ENV=production - for production deployments
    # - DJANGO_ENV=staging - for staging environment
    # - DJANGO_ENV=test - for running tests
    #
    # Example:
    #   DJANGO_ENV=production python manage.py runserver
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.settings")
    os.environ.setdefault("DJANGO_ENV", "development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
