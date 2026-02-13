# Template Backend - Development Guide

This guide covers setting up a development environment, contributing to the project, and following best practices.

## Prerequisites

### Required Software

- **Python** 3.10 or higher
- **Git** - Latest version
- **Docker Desktop** (optional) - For running database and Redis locally
- **PostgreSQL** 14+ or use Docker services
- **Redis** 6+ or use Docker services
- **RabbitMQ** 3.12+ or use Docker services

### Recommended Tools

- **IDE**: VS Code, PyCharm, or Vim
- **API Client**: Postman, Insomnia, or Hoppscotch
- **Database Tool**: TablePlus, pgAdmin, or DataGrip
- **Redis GUI**: Another Redis Desktop

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/template-backend.git
cd template-backend
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 4. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env

# Edit .env with your settings
# Windows: notepad .env
# macOS/Linux: nano .env
```

**Required Settings:**

- `DJANGO_ENV=development`
- `SECRET_KEY` - Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT_NUMBER`
- `REDIS_HOST`, `REDIS_PORT_NUMBER`, `REDIS_PASSWORD`

### 5. Run Migrations

```bash
# Create and apply migrations
python src/manage.py makemigrations
python src/manage.py migrate
```

### 6. Create Superuser

```bash
python src/manage.py createsuperuser --email admin@example.com --noinput
```

### 7. Start Development Server

```bash
# Default: port 8000
python src/manage.py runserver

# Custom port
python src/manage.py runserver 0.0.0.0:8080
```

### 8. Access Django Shell

```bash
# Standard shell
python src/manage.py shell

# Enhanced shell (with all models imported)
python src/manage.py shell_plus
```

### 9. Access Django Admin

```
url: http://localhost:8000/admin/
```

## Working with Docker

### Start All Services

```bash
docker-compose up --build
```

### Stop All Services

```bash
docker-compose down
```

### Restart Specific Service

```bash
docker-compose restart web
docker-compose restart db
docker-compose restart redis
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
```

### Run Commands in Container

```bash
# Django shell
docker-compose exec web python src/manage.py shell_plus

# Run migrations
docker-compose exec web python src/manage.py migrate

# Collect static files
docker-compose exec web python src/manage.py collectstatic
```

## Database Access

### Using psql

```bash
# Connect to database
docker-compose exec db psql -U postgres

# List databases
\l

# Quit
\q
```

### Using TablePlus

1. Create new connection:
   - Host: `localhost`
   - Port: `5432`
   - Database: `template_dev`
   - User: `postgres`
   - Password: `<your password>`

2. Advanced:
   - Enable SSH tunneling for remote databases
   - Save connection profiles

## Running Tests

### Using pytest

```bash
# Run all tests
pytest

# Run specific test file
pytest src/tests/test_subscription.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run only failed tests from last run
pytest --lf

# Run tests matching pattern
pytest -k "test_subscription" -v
```

### Using test database

```bash
pytest --ds=settings.test_settings
```

## Code Quality

### Running Linters

```bash
# Ruff linter
ruff check src/

# Ruff formatter
ruff format src/

# Type checking
mypy src/

# Security audit
bandit -r src/
```

### Auto-fixing Issues

```bash
# Ruff auto-fix
ruff check --fix src/

# Import sorting
isort src/

# Apply all fixes
make lint-fix
```

## Debugging

### Django Debug Toolbar

Access at: `http://localhost:8000/debug/`

Features:

- SQL query analysis
- Cache performance tracking
- Request profiling

### Using pdb

```bash
# Add breakpoint
python -m pdb src/manage.py runserver

# Then trigger breakpoint from browser
```

### Logging

Logs are stored in `src/logs/`:

- `django.log` - General Django logs
- Celery logs

View real-time logs:

```bash
tail -f src/logs/django.log
```

## API Testing

### Using curl

```bash
# Login and get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}'

# Use token for authenticated request
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <your_token>"

# Subscribe to plan
curl -X POST http://localhost:8000/api/subscriptions/subscribe \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 2}'
```

### Using Postman

1. Import collection from `docs/postman_collection.json`
2. Set environment variable: `{{base_url}}` = `http://localhost:8000`
3. Use `{{access_token}}` variable for auth
4. Set `{{refresh_token}}` for token refresh

## Common Issues & Solutions

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /IM python.exe

# macOS/Linux
lsof -ti :8000
kill -9 $(lsof -ti :8000)
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check logs
docker-compose logs db

# Restart services
docker-compose restart db
```

### Migration Conflicts

```bash
# Fake migrations
python src/manage.py fake migrations --list

# Clear migration history
find src/*/migrations/ -name "*.py" -delete
```

### Static Files Not Loading

```bash
# Collect static files
python src/manage.py collectstatic --noinput

# Clear cache
ruff cache --clear
```

## Best Practices

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all classes, methods, and modules
- Keep functions focused and single-purpose
- Maximum line length: 88 characters

### Git Workflow

1. Create feature branch: `git checkout -b feature/amazing-feature`
2. Make changes and test
3. Commit: `git commit -m "feat(subscription): Add monthly tier"`
4. Push: `git push origin feature/amazing-feature`
5. Create pull request on GitHub

### Testing

- Write tests for all new features
- Aim for >80% code coverage
- Use factory pattern for test data
- Mock external services (Stripe, email)

### Security

- Never commit `.env` file
- Use environment variables for secrets
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Rate limit all public endpoints

## Project Structure

```
src/
├── configuration/       # Django settings
│   ├── settings/      # Modular settings (dev/prod/test)
├── myapp/            # Main application
│   ├── models/        # Modular models (domain-based)
│   │   ├── base.py     # Base model classes
│   │   ├── choices.py   # Choice definitions
│   │   ├── features.py  # Generic feature flags
│   │   └── ...          # Domain models
│   ├── apis/          # API endpoints (organized by domain)
│   ├── services/       # Business logic services
│   ├── serializers/    # DRF serializers
│   ├── middleware/     # Custom middleware
│   └── utils/         # Helper utilities
└── manage.py          # Django management script
```

## Contributing Guidelines

1. Follow the code style guidelines
2. Write tests for new functionality
3. Update documentation as needed
4. Keep commits atomic and focused
5. Write descriptive commit messages

## Getting Help

- Create an issue on GitHub
- Check existing issues first
- Provide clear reproduction steps
- Include error messages and stack traces

---

**Last Updated:** February 11, 2025
