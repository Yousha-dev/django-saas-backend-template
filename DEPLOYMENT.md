# Template Backend - Production Deployment Guide

Complete production deployment guide for Template Backend using Docker and Docker Compose.

## Quick Start

### Build and Start

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up --build
```

## Environment Setup

### Production Environment File

Copy `.env.example` to `.env.prod` and configure:

```bash
cp .env.example .env.prod
```

**Required Variables:**

```bash
# Django
DJANGO_ENV=production
DEBUG=False

# Secret Key (generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
SECRET_KEY=<strong-random-production-key>

# Database (use RDS, CloudSQL, or managed PostgreSQL)
DB_NAME=template_prod
DB_USER=template_user
DB_PASSWORD=<strong-production-password>
DB_HOST=<production-db-host>
DB_PORT_NUMBER=5432

# Redis (use ElastiCache or managed Redis)
REDIS_HOST=<your-redis-host>
REDIS_PORT_NUMBER=6379
REDIS_PASSWORD=<strong-redis-password>

# RabbitMQ (use managed MQ)
RABBITMQ_USER=<your-mq-user>
RABBITMQ_PASSWORD=<strong-mq-password>
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT_NUMBER=5672

# Email
EMAIL_HOST=smtp.sendgrid.com
EMAIL_PORT=587
EMAIL_HOST_USER=notifications@yourdomain.com
EMAIL_HOST_PASSWORD=<sendgrid-password>
EMAIL_USE_TLS=True

# Stripe (use live keys in production)
STRIPE_ENABLED=True
STRIPE_SECRET_KEY=sk_live_<your-live-secret-key>
STRIPE_PUBLISHABLE_KEY=pk_live_<your-live-publishable-key>

# URLs
FRONTEND_URL=https://yourdomain.com
API_URL=https://api.yourdomain.com
```

## Building Images

### Production Image

```bash
# Build and tag production image
docker build -t template-backend:latest .
docker tag template-backend:latest <registry-url>/template-backend:latest
docker push <registry-url>/template-backend:latest
```

## Running Services

### Start All Services

```bash
docker-compose -f docker-compose.prod.yml up --build
```

### Health Checks

```bash
# API health check
curl http://localhost:8000/api/health/

# Database health
docker-compose exec db pg_isready -U <DB_USER> -d <DB_NAME>

# Redis health
docker-compose exec redis redis-cli ping

# RabbitMQ health
docker-compose exec rabbitmq rabbitmq-diagnostics -q ping
```

## Deployment to Cloud

See `API/DEPLOYMENT.md` for AWS ECS deployment instructions.

### DigitalOcean

See `API/DEPLOYMENT.md` for DigitalOcean deployment instructions.

---

**Last Updated:** February 11, 2025
