"""
WSGI config for this project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/

Environment Selection:
    Set the DJANGO_ENV environment variable to select the appropriate settings:
    - DJANGO_ENV=development (default) - for local development
    - DJANGO_ENV=production - for production deployments
    - DJANGO_ENV=staging - for staging environment
    - DJANGO_ENV=test - for running tests
"""

import os

from django.core.wsgi import get_wsgi_application

# Set the default Django settings module
# In production, set DJANGO_ENV=production in your web server config
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.settings")

application = get_wsgi_application()
