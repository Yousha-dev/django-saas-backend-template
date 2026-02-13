"""
ASGI config for this project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/

Environment Selection:
    Set the DJANGO_ENV environment variable to select the appropriate settings:
    - DJANGO_ENV=development (default) - for local development
    - DJANGO_ENV=production - for production deployments
    - DJANGO_ENV=staging - for staging environment
    - DJANGO_ENV=test - for running tests
"""

import os

import django
from django.core.asgi import get_asgi_application

# Set Django settings FIRST
# In production, set DJANGO_ENV=production in your ASGI server config
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.settings")

# Initialize Django BEFORE importing anything that uses models
django.setup()

# Now import channels and routing (after Django is setup)
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from myapp.routing import websocket_urlpatterns  # noqa: E402

# Create ASGI application
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
