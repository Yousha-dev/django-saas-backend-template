#!/bin/bash
# filepath: c:\office\Template-Backend\entrypoint.sh

# Set script to exit on any errors.
set -e

# Wait for database to be ready
echo "Waiting for database to be ready..."
python3 -c "
import os
import psycopg2
import time

max_tries = 30
for i in range(max_tries):
    try:
        conn = psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            port=os.environ.get('DB_PORT_NUMBER')
        )
        conn.close()
        print('Database is ready!')
        break
    except psycopg2.OperationalError:
        if i == max_tries - 1:
            raise
        print(f'Database not ready, waiting... ({i+1}/{max_tries})')
        time.sleep(2)
"

# Run database migrations
# echo "Performing database migrations..."
# python3 manage.py makemigrations
# python3 manage.py migrate
# echo "Database migrations completed."

# Collect static files (optional)
# echo "Collecting static files..."
# python3 manage.py collectstatic --noinput || echo "Static files collection failed, continuing..."

# Create superuser if needed (optional)
# echo "Checking for superuser..."
# python3 manage.py shell -c "
# from django.contrib.auth import get_user_model;
# User = get_user_model();
# if not User.objects.filter(is_superuser=True).exists():
#     User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
#     print('Superuser created: admin / admin123')
# else:
#     print('Superuser already exists')
# " || echo "Superuser creation skipped"

# Start the Django development server
echo "Starting Django server..."
# python3 manage.py runserver 0.0.0.0:8000

# For production, use gunicorn or uvicorn:
# gunicorn --bind 0.0.0.0:8000 --workers 4 configuration.wsgi:application --log-level=info --timeout 500
# OR for ASGI support:
# uvicorn configuration.asgi:application --host 0.0.0.0 --port 8000 --log-level info --timeout-keep-alive 500
# daphne -p 8000 configuration.asgi:application
