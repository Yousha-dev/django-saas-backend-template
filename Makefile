# =============================================================================
# Template Backend - Makefile
# =============================================================================
# Provides shortcuts for common development tasks.
#
# Usage:
#   make <target>        # Run a target
#   make help             # Show all available targets
# =============================================================================

.PHONY: help install install-dev update-deps \
		clean clean-all clean-cache clean-db clean-pyc \
		migrate makemigrations createsuperuser \
		run run-dev run-prod shell shell-plus \
		test test-cov test-watch lint lint-fix format check \
		docker-build docker-up docker-down docker-logs \
		django-check check-security

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# VARIABLES
# =============================================================================

PYTHON := python
MANAGE := $(PYTHON) src/manage.py
PYTEST := pytest
RUFF := ruff
PRECOMMIT := pre-commit

# =============================================================================
# HELP TARGET
# =============================================================================

help:  ## Show this help message
	@echo '\n$(PROJECT_NAME) - Available targets:\n'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# INSTALLATION
# =============================================================================

install:  ## Install production dependencies
	@echo "Installing production dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

install-dev:  ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PRECOMMIT) install

update-deps:  ## Update all dependencies
	@echo "Updating dependencies..."
	$(PYTHON) -m pip install --upgrade -r requirements.txt
	$(PYTHON) -m pip install --upgrade -r requirements-dev.txt

# =============================================================================
# CLEANUP
# =============================================================================

clean: clean-pyc clean-cache  ## Clean all generated files
	@echo "Cleaned all generated files"

clean-all: clean clean-db  ## Clean everything including database
	@echo "Deep clean completed"

clean-pyc:  ## Remove Python cache files
	@echo "Removing Python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.pyc" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.pyo" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	find . -type f -name "*.cover" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true

clean-cache:  ## Remove Django cache and static files
	@echo "Removing Django cache and static files..."
	rm -rf src/staticfiles/ 2>/dev/null || true
	rm -rf src/media/__pycache__/ 2>/dev/null || true

clean-db:  ## Remove database file (SQLite only)
	@echo "Removing database files..."
	rm -f src/db.sqlite3 2>/dev/null || true
	@echo "Note: PostgreSQL databases are not removed by this target"

# =============================================================================
# DJANGO MANAGEMENT
# =============================================================================

migrate:  ## Run database migrations
	@echo "Running database migrations..."
	$(MANAGE) migrate

makemigrations:  ## Create new migrations
	@echo "Creating new migrations..."
	$(MANAGE) makemigrations

makemigrations-empty name=$(name):  ## Create empty migration with name
	@echo "Creating empty migration: $(name)..."
	$(MANAGE) makemigrations --empty $(name)

createsuperuser:  ## Create a superuser
	@echo "Creating superuser..."
	$(MANAGE) createsuperuser

collectstatic:  ## Collect static files
	@echo "Collecting static files..."
	$(MANAGE) collectstatic --noinput

shell:  ## Open Django shell
	@echo "Opening Django shell..."
	$(MANAGE) shell

shell-plus:  ## Open Django shell+ (with all models imported)
	@echo "Opening Django shell-plus..."
	$(MANAGE) shell_plus

show-config:  ## Show current Django configuration
	$(MANAGE) show_settings 2>/dev/null || $(MANAGE) diffsettings

# =============================================================================
# DJANGO CHECKS
# =============================================================================

django-check:  ## Run Django system checks
	@echo "Running Django system checks..."
	$(MANAGE) check --deploy

check-security:  ## Run Django security checks
	@echo "Running Django security checks..."
	$(MANAGE) check --deploy

check: django-check lint  ## Run all checks (Django + linting)

# =============================================================================
# CODE QUALITY
# =============================================================================

lint:  ## Run linters (ruff, mypy, bandit)
	@echo "Running linters..."
	@echo "=================================="
	@echo "Ruff linter..."
	$(RUFF) check src/
	@echo "=================================="
	@echo "Mypy type checker..."
	mypy src/
	@echo "=================================="
	@echo "Bandit security linter..."
	bandit -r src/ -c pyproject.toml
	@echo "=================================="
	@echo "All linters passed!"

lint-fix:  ## Auto-fix linting issues
	@echo "Auto-fixing linting issues..."
	$(RUFF) check --fix src/
	@echo "Linting issues auto-fixed. Run 'make lint' to verify."

format:  ## Format code with ruff
	@echo "Formatting code..."
	$(RUFF) format src/
	@echo "Code formatted successfully!"

format-check:  ## Check if code is formatted
	@echo "Checking code formatting..."
	$(RUFF) format --check src/

check: lint format-check  ## Run all quality checks

# =============================================================================
# TESTING
# =============================================================================

test:  ## Run tests
	@echo "Running tests..."
	DJANGO_ENV=test $(PYTEST) -v

test-cov:  ## Run tests with coverage report
	@echo "Running tests with coverage..."
	DJANGO_ENV=test $(PYTEST) --cov=src --cov-report=term-missing --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:  ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	DJANGO_ENV=test $(PYTEST) -f

test-unit:  ## Run unit tests only
	@echo "Running unit tests..."
	DJANGO_ENV=test $(PYTEST) -m "not integration" -v

test-integration:  ## Run integration tests only
	@echo "Running integration tests..."
	DJANGO_ENV=test $(PYTEST) -m "integration" -v

test-failed:  ## Run only failed tests from last run
	@echo "Running failed tests..."
	DJANGO_ENV=test $(PYTEST) --lf -v

# =============================================================================
# DEVELOPMENT SERVER
# =============================================================================

run: run-dev  ## Start development server (default)

run-dev:  ## Start development server
	@echo "Starting development server..."
	$(MANAGE) runserver 0.0.0.0:8000

run-prod:  ## Start production server with gunicorn
	@echo "Starting production server..."
	gunicorn configuration.wsgi:application \
		--bind 0.0.0.0:8000 \
		--workers 4 \
		--threads 4 \
		--worker-class gthread \
		--timeout 120 \
		--access-logfile - \
		--error-logfile - \
		--log-level info

run-asgi:  ## Start ASGI server for WebSockets
	@echo "Starting ASGI server..."
	uvicorn configuration.asgi:application \
		--host 0.0.0.0 \
		--port 8000 \
		--workers 4 \
		--log-level info

# =============================================================================
# CELERY
# =============================================================================

celery-worker:  ## Start Celery worker
	@echo "Starting Celery worker..."
	celery -A configuration worker --loglevel=info

celery-beat:  ## Start Celery beat scheduler
	@echo "Starting Celery beat scheduler..."
	celery -A configuration beat --loglevel=info

celery-flower:  ## Start Celery Flower monitoring
	@echo "Starting Celery Flower..."
	celery -A configuration flower --port=5555

# =============================================================================
# DOCKER
# =============================================================================

docker-build:  ## Build Docker containers
	@echo "Building Docker containers..."
	docker-compose build

docker-up:  ## Start Docker containers
	@echo "Starting Docker containers..."
	docker-compose up -d

docker-down:  ## Stop Docker containers
	@echo "Stopping Docker containers..."
	docker-compose down

docker-logs:  ## Show Docker container logs
	docker-compose logs -f

docker-shell:  ## Open shell in Django container
	docker-compose exec web bash

docker-migrate:  ## Run migrations in Docker container
	docker-compose exec web python src/manage.py migrate

docker-makemigrations:  ## Create migrations in Docker container
	docker-compose exec web python src/manage.py makemigrations

docker-createsuperuser:  ## Create superuser in Docker container
	docker-compose exec web python src/manage.py createsuperuser

# =============================================================================
# PRE-COMMIT
# =============================================================================

pre-commit:  ## Run pre-commit hooks manually
	@echo "Running pre-commit hooks..."
	$(PRECOMMIT) run --all-files

pre-commit-update:  ## Update pre-commit hooks to latest versions
	@echo "Updating pre-commit hooks..."
	$(PRECOMMIT) autoupdate

# =============================================================================
# MISC
# =============================================================================

deps-tree:  ## Show dependency tree
	@echo "Generating dependency tree..."
	$(PYTHON) -m pipdeptree

deps-outdated:  ## Show outdated dependencies
	@echo "Checking for outdated dependencies..."
	$(PYTHON) -m pip list --outdated

requirements-update:  ## Update requirements.txt from current environment
	@echo "Updating requirements.txt..."
	$(PYTHON) -m pip freeze > requirements.txt.new
	mv requirements.txt.new requirements.txt

install-pre-commit:  ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	$(PRECOMMIT) install

# =============================================================================
# DOCUMENTATION
# =============================================================================

docs:  ## Generate documentation
	@echo "Generating documentation..."
	cd docs && make html

docs-serve:  ## Serve documentation locally
	@echo "Serving documentation at http://localhost:8000"
	cd docs && python -m http.server 8000

# =============================================================================
# PROJECT INFO
# =============================================================================

info:  ## Show project information
	@echo "Project: Template Backend"
	@echo "Python version:"
	@$(PYTHON) --version
	@echo "\nInstalled packages:"
	@$(PYTHON) -m pip list
