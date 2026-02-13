"""
Basic tests for Template Backend - Minimal smoke tests.
"""

import pytest


@pytest.mark.unit
class TestDjangoConfiguration:
    """Test that Django is configured correctly."""

    def test_django_is_configured(self):
        """Test that Django settings can be loaded."""
        from django.conf import settings

        assert settings.DJANGO_ENV is not None

    def test_installed_apps(self):
        """Test that required apps are installed."""
        from django.conf import settings

        required_apps = ["django.contrib.auth", "rest_framework", "myapp"]
        for app in required_apps:
            assert app in settings.INSTALLED_APPS

    def test_database_configured(self):
        """Test that database is configured."""
        from django.conf import settings

        assert settings.DATABASES is not None
        assert "default" in settings.DATABASES


@pytest.mark.unit
class TestModelsImport:
    """Test that models can be imported."""

    def test_import_models(self):
        """Test that models can be imported."""
        from myapp.models import (
            User,
        )

        assert User is not None
