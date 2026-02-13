import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "configuration.settings")

# Create the Celery app instance
app = Celery("configuration")

# Load configuration from Django settings (this picks up everything from settings.py)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all Django apps
app.autodiscover_tasks()


# Optional debug task
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# DON'T duplicate beat_schedule or task_routes here - they're already in settings.py
