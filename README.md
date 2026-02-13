# Django Backend Template

A production-ready Django REST API backend for SaaS subscription management, user authentication, payment processing, content moderation, and business analytics.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Configuration](#environment-configuration)
  - [Database Setup](#database-setup)
  - [Running the Server](#running-the-server)
- [Docker Setup](#docker-setup)
- [API Reference](#api-reference)
  - [Authentication APIs](#authentication-apis)
  - [Core APIs](#core-apis)
  - [Admin APIs](#admin-apis)
  - [Payment APIs](#payment-apis)
- [Services](#services)
- [Models](#models)
- [Middleware](#middleware)
- [Payment System](#payment-system)
- [Feature Flags](#feature-flags)
- [Celery Tasks](#celery-tasks)
- [Notifications](#notifications)
- [Internationalization (i18n)](#internationalization-i18n)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Deployment](#deployment)
- [Makefile Commands](#makefile-commands)
- [Troubleshooting](#troubleshooting)

---

## Overview

This Django Backend Template provides a complete SaaS backend with:

- **User Management** — Registration, JWT authentication, profile management, role-based access
- **Subscription Management** — Tiered plans with generic feature flags, billing, auto-renewal
- **Payment Processing** — Strategy pattern with Stripe, PayPal, Bank Transfer, Apple IAP, Google Play
- **Content Management** — Posts, comments, moderation queue with appeals
- **Event & Reminder System** — Calendar events, automated email reminders
- **Analytics** — Monthly aggregation, dashboard stats, subscription analytics
- **Notifications** — Multi-channel (email, SMS, push) via SendGrid, Twilio, Firebase
- **Discount & Referral System** — Coupons, referral codes, reward tracking
- **Rate Limiting** — Subscription-based API rate limiting per user

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client / Frontend                        │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                     Django REST Framework                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Auth API │  │ Core API │  │Admin API │  │ Payment API   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬────────┘   │
│       │              │             │               │            │
│  ┌────▼──────────────▼─────────────▼───────────────▼────────┐   │
│  │                   Service Layer                          │   │
│  │  Subscription · Payment · Notification · Analytics       │   │
│  │  Discount · Referral · Moderation · Refund               │   │
│  └────┬──────────────┬─────────────┬───────────────┬────────┘   │
│       │              │             │               │            │
│  ┌────▼────┐   ┌─────▼────┐  ┌────▼────┐   ┌──────▼───────┐   │
│  │ Models  │   │ Celery   │  │ Cache   │   │ Payment      │   │
│  │ (ORM)   │   │ Tasks    │  │ (Redis) │   │ Strategies   │   │
│  └────┬────┘   └─────┬────┘  └─────────┘   └──────┬───────┘   │
└───────┼──────────────┼─────────────────────────────┼───────────┘
        │              │                             │
   ┌────▼────┐   ┌─────▼──────┐              ┌──────▼───────┐
   │PostgreSQL│   │ RabbitMQ   │              │Stripe/PayPal │
   └─────────┘   └────────────┘              └──────────────┘
```

### Middleware Pipeline

```
Request → SecurityMiddleware → CORS → Session → Locale → Common → CSRF
        → Auth → Messages → XFrame → RequestLogging → RateLimit → Language
        → View → Response
```

---

## Technology Stack

| Component      | Technology                             | Version |
| -------------- | -------------------------------------- | ------- |
| Framework      | Django                                 | 5.2+    |
| API            | Django REST Framework                  | 3.15+   |
| Database       | PostgreSQL                             | 14+     |
| Cache          | Redis                                  | 6+      |
| Message Broker | RabbitMQ                               | 3.12+   |
| Task Queue     | Celery + django-celery-beat            | 5.2+    |
| Authentication | SimpleJWT                              | 5.0+    |
| API Docs       | drf-yasg (Swagger/OpenAPI)             | 1.20+   |
| Payment        | Stripe, PayPal, Apple IAP, Google Play | —       |
| Notifications  | SendGrid, Twilio, Firebase Admin       | —       |
| WebSockets     | Django Channels + channels-redis       | 4.0+    |
| Logging        | structlog + python-json-logger         | 24.0+   |
| WSGI Server    | Gunicorn + gevent                      | 21.0+   |
| ASGI Server    | Uvicorn                                | 0.30+   |
| Python         | CPython                                | 3.12+   |

---

## Project Structure

```
Template-Backend/
├── docker-compose.yml          # Infrastructure services (PostgreSQL, Redis, RabbitMQ)
├── docker-compose.prod.yml     # Production Docker Compose
├── Dockerfile                  # Application Docker image
├── Dockerfile.prod             # Production Docker image
├── entrypoint.sh               # Docker entrypoint script
├── Makefile                    # Development shortcuts
├── pyproject.toml              # Python project configuration (ruff, etc.)
├── pytest.ini                  # Test configuration
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── env.example                 # Environment variables template
│
└── src/                        # Application source code
    ├── manage.py               # Django management entry point
    │
    ├── configuration/          # Django project settings
    │   ├── __init__.py
    │   ├── asgi.py             # ASGI application
    │   ├── wsgi.py             # WSGI application
    │   ├── celery.py           # Celery application configuration
    │   ├── urls.py             # Root URL configuration
    │   ├── jwt_settings.py     # JWT token configuration
    │   └── settings/           # Environment-specific settings
    │       ├── __init__.py     # Auto-selects environment (dev/prod/staging/test)
    │       ├── base.py         # Shared settings
    │       ├── development.py  # Development overrides
    │       ├── production.py   # Production hardening
    │       ├── staging.py      # Staging settings
    │       └── test.py         # Test-optimized settings
    │
    ├── myapp/                  # Main application
    │   ├── admin.py            # Django admin configuration
    │   ├── apps.py             # App configuration
    │   ├── authentication.py   # Custom JWT authentication class
    │   ├── emailhelper.py      # Email sending utilities
    │   ├── middleware.py       # Custom middleware (JWT, rate limit, logging, i18n)
    │   ├── permissions.py      # Custom DRF permissions
    │   ├── routing.py          # WebSocket routing
    │   │
    │   ├── apis/               # API views organized by domain
    │   │   ├── auth/           # Authentication endpoints
    │   │   ├── core/           # User-facing endpoints
    │   │   │   ├── content/    # Posts & comments
    │   │   │   ├── discounts/  # Coupon validation & application
    │   │   │   ├── events/     # Calendar events
    │   │   │   ├── notifications/  # User notifications
    │   │   │   ├── referrals/  # Referral system
    │   │   │   └── reminders/  # Reminders
    │   │   ├── admin/          # Admin-only endpoints
    │   │   │   ├── subscriptions/      # Subscription management
    │   │   │   └── subscriptionplans/  # Plan CRUD & analytics
    │   │   └── payment/        # Payment processing
    │   │
    │   ├── models/             # Database models
    │   │   ├── base.py         # Abstract base models
    │   │   ├── user.py         # User, UserManager, Role
    │   │   ├── subscription.py # SubscriptionPlan, Subscription, Payment, Renewal
    │   │   ├── event.py        # Event, Reminder
    │   │   ├── notification.py # Notification
    │   │   ├── features.py     # FeatureFlags, FeatureDefinition
    │   │   ├── analytics.py    # MonthlyAnalytics
    │   │   ├── logging.py      # ActivityLog, AuditLog
    │   │   ├── choices.py      # All enum/choice classes
    │   │   └── ...             # content, moderation, discount, referral
    │   │
    │   ├── serializers/        # DRF serializers
    │   ├── services/           # Business logic layer
    │   │   ├── subscription_service.py
    │   │   ├── notification_service.py
    │   │   ├── analytics_service.py
    │   │   ├── moderation_service.py
    │   │   └── payment/        # Payment sub-services
    │   │       ├── payment_service.py  # Orchestrator
    │   │       ├── discount.py         # Coupon logic
    │   │       ├── referral.py         # Referral logic
    │   │       └── refund.py           # Refund processing
    │   │
    │   ├── payment_strategies/ # Strategy pattern for payments
    │   │   ├── base.py         # Abstract PaymentProvider, PaymentResult, WebhookEvent
    │   │   ├── factory.py      # PaymentProviderFactory, PaymentManager
    │   │   ├── webhooks.py     # Webhook handlers (Stripe, PayPal)
    │   │   └── providers/      # Concrete provider implementations
    │   │       ├── stripe.py
    │   │       ├── paypal.py
    │   │       ├── bank_transfer.py
    │   │       ├── apple_iap.py
    │   │       └── google_play.py
    │   │
    │   ├── tasks/              # Celery async tasks
    │   └── utils/              # Utilities (caching, logging)
    │
    ├── tests/                  # Test suite
    │   ├── conftest.py         # Shared fixtures
    │   ├── test_api.py         # API integration tests
    │   ├── test_services.py    # Service unit tests
    │   ├── test_middleware.py  # Middleware tests
    │   ├── test_tasks.py       # Celery task tests
    │   ├── test_webhooks.py    # Webhook handler tests
    │   ├── test_models.py      # Model tests
    │   └── test_basic.py       # Smoke tests
    │
    └── locale/                 # Translation files
```

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose** (for PostgreSQL, Redis, RabbitMQ)
- **Git**

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/template-backend.git
cd template-backend

# 2. (Optional) Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# For development (includes ruff, pytest, pre-commit):
pip install -r requirements-dev.txt
```

### Environment Configuration

```bash
# Copy the example environment file
cp env.example .env
```

Edit `.env` with your configuration:

```env
# =============================================================================
# DJANGO
# =============================================================================
SECRET_KEY="your-secret-key-here"
DEBUG="True"
DJANGO_PORT=8888

# =============================================================================
# JWT
# =============================================================================
JWT_SIGNING_KEY="your-jwt-signing-key"
JWT_ACCESS_TOKEN_LIFETIME_DAYS=10
JWT_REFRESH_TOKEN_LIFETIME_DAYS=15

# =============================================================================
# PostgreSQL
# =============================================================================
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT_NUMBER=5432

# =============================================================================
# Redis
# =============================================================================
REDIS_HOST=localhost
REDIS_PORT_NUMBER=6379
REDIS_PASSWORD=your-redis-password

# =============================================================================
# RabbitMQ
# =============================================================================
RABBITMQ_HOST=localhost
RABBITMQ_PORT_NUMBER=5672
RABBITMQ_USER=rabbitmq
RABBITMQ_PASSWORD=your-rabbitmq-password

# =============================================================================
# Email (SendGrid)
# =============================================================================
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
EMAIL_USE_TLS=True

# =============================================================================
# Stripe
# =============================================================================
STRIPE_ENABLED="False"
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_PUBLISHABLE_KEY="pk_test_..."

# =============================================================================
# URLs
# =============================================================================
FRONTEND_URL=http://localhost:3000
API_URL=http://localhost:8888
```

### Environment Selection

The settings module auto-selects based on `DJANGO_ENV`:

| `DJANGO_ENV` value                  | Settings file    | Use case              |
| ----------------------------------- | ---------------- | --------------------- |
| `development` / `dev` / _(not set)_ | `development.py` | Local development     |
| `production` / `prod`               | `production.py`  | Production deployment |
| `staging` / `stage`                 | `staging.py`     | Staging/QA            |
| `test` / `testing`                  | `test.py`        | Running tests         |

### Database Setup

```bash
# 1. Start infrastructure services
docker-compose up -d

# 2. Run migrations
cd src
python manage.py migrate

# 3. Create a superuser (admin)
python manage.py createsuperuser

# 4. (Optional) Seed subscription plans
python manage.py shell -c "
from myapp.models import SubscriptionPlan
from django.utils import timezone
SubscriptionPlan.objects.create(
    name='Free', description='Free tier', monthly_price=0, yearly_price=0,
    max_api_calls_per_hour=50, is_active=1, is_deleted=0,
    feature_details='Basic access', created_at=timezone.now(), created_by=1
)
SubscriptionPlan.objects.create(
    name='Pro', description='Professional plan', monthly_price=29.99, yearly_price=299.99,
    max_api_calls_per_hour=5000, is_active=1, is_deleted=0,
    feature_details='All features', created_at=timezone.now(), created_by=1
)
print('Plans created!')
"
```

### Running the Server

```bash
cd src

# Development server
python manage.py runserver 0.0.0.0:8888

# Production (Gunicorn)
gunicorn configuration.wsgi:application --bind 0.0.0.0:8000 --workers 4

# ASGI (Uvicorn — for WebSocket support)
uvicorn configuration.asgi:application --host 0.0.0.0 --port 8000
```

After starting, visit:

- **Swagger UI**: http://localhost:8888/swagger/
- **ReDoc**: http://localhost:8888/redoc/
- **Admin Panel**: http://localhost:8888/admin/

---

## Docker Setup

### Development (Infrastructure Only)

Start only PostgreSQL, Redis, and RabbitMQ — run Django locally:

```bash
docker-compose up -d
cd src && python manage.py runserver 0.0.0.0:8888
```

### Production (Full Stack)

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Docker Services

| Service    | Image             | Default Port | Purpose                       |
| ---------- | ----------------- | ------------ | ----------------------------- |
| `db`       | `postgres:latest` | 5432         | Primary database              |
| `redis`    | `redis:latest`    | 6379         | Cache & Celery result backend |
| `rabbitmq` | `rabbitmq:latest` | 5672         | Celery message broker         |

### Docker Commands

```bash
docker-compose up -d          # Start services
docker-compose down           # Stop services
docker-compose logs -f db     # View database logs
docker-compose ps             # List running services
```

---

## API Reference

All endpoints require JWT authentication unless noted. Use the `Authorization: Bearer <token>` header.

The full interactive API documentation is available at `/swagger/` when the server is running.

### Authentication APIs

**Base path:** `/api/auth/`

| Method   | Endpoint                   | Description                          | Auth |
| -------- | -------------------------- | ------------------------------------ | ---- |
| `POST`   | `/register/`               | Register user with subscription plan | No   |
| `POST`   | `/register-user/`          | Register user only                   | No   |
| `POST`   | `/login/`                  | Login and receive JWT tokens         | No   |
| `POST`   | `/api/token/`              | Obtain JWT token pair                | No   |
| `POST`   | `/request-password-reset/` | Request password reset email         | No   |
| `POST`   | `/reset-password/`         | Reset password with token            | No   |
| `POST`   | `/users/change-password/`  | Change current password              | Yes  |
| `POST`   | `/users/deactivate-user/`  | Deactivate user account              | Yes  |
| `DELETE` | `/users/delete-user/`      | Permanently delete user              | Yes  |
| `GET`    | `/subscriptionplans/`      | List available subscription plans    | No   |
| `POST`   | `/payment/create-intent/`  | Create Stripe payment intent         | Yes  |
| `GET`    | `/payment/status/`         | Check payment service health         | Yes  |
| `POST`   | `/send-email/`             | Send email notification              | Yes  |

#### Example: Login

```bash
curl -X POST http://localhost:8888/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

Response:

```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "refresh": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "user_id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "user"
  }
}
```

---

### Core APIs

**Base path:** `/api/core/` — All endpoints require authentication.

#### User Profile

| Method      | Endpoint        | Description              |
| ----------- | --------------- | ------------------------ |
| `GET`       | `/user/`        | Get current user profile |
| `PUT/PATCH` | `/user/update/` | Update user profile      |

#### Subscriptions

| Method | Endpoint                | Description                   |
| ------ | ----------------------- | ----------------------------- |
| `GET`  | `/subscription/`        | Get current user subscription |
| `GET`  | `/subscription/stats/`  | Subscription stats & usage    |
| `GET`  | `/subscription/health/` | Subscription validity check   |
| `GET`  | `/subscription/limits/` | Check API/operation limits    |
| `GET`  | `/subscription/plans/`  | List available plans          |
| `POST` | `/subscription/change/` | Change subscription plan      |
| `GET`  | `/features/`            | Get user's feature flags      |

#### Events

| Method      | Endpoint                                 | Description                     |
| ----------- | ---------------------------------------- | ------------------------------- |
| `POST`      | `/events/create/`                        | Create a new event              |
| `GET`       | `/events/list/`                          | List user's events              |
| `PUT/PATCH` | `/events/<id>/update/`                   | Update an event                 |
| `DELETE`    | `/events/<id>/delete/`                   | Delete an event                 |
| `GET/POST`  | `/events/auto-send-action-email-event`   | Auto-send action event emails   |
| `GET/POST`  | `/events/auto-send-reminder-email-event` | Auto-send reminder event emails |

#### Notifications

| Method   | Endpoint                            | Description               |
| -------- | ----------------------------------- | ------------------------- |
| `POST`   | `/notifications/create/`            | Create a notification     |
| `GET`    | `/notifications/list/`              | List user's notifications |
| `DELETE` | `/notifications/<id>/delete/`       | Delete a notification     |
| `DELETE` | `/notifications/clear-all/`         | Clear all notifications   |
| `PATCH`  | `/notifications/<id>/mark-as-read/` | Mark notification as read |

#### Reminders

| Method     | Endpoint                               | Description                 |
| ---------- | -------------------------------------- | --------------------------- |
| `POST`     | `/reminders/create/`                   | Create a reminder           |
| `GET`      | `/reminders/list/`                     | List user's reminders       |
| `DELETE`   | `/reminders/<id>/delete/`              | Delete a reminder           |
| `POST`     | `/reminders/<id>/send-email-reminder/` | Send reminder email         |
| `GET/POST` | `/reminders/auto-send-email-reminder/` | Auto-send pending reminders |

#### Discounts

| Method | Endpoint               | Description                  |
| ------ | ---------------------- | ---------------------------- |
| `POST` | `/discounts/validate/` | Validate a coupon code       |
| `POST` | `/discounts/apply/`    | Apply a coupon to a purchase |

#### Referrals

| Method | Endpoint               | Description              |
| ------ | ---------------------- | ------------------------ |
| `POST` | `/referrals/generate/` | Generate a referral code |
| `POST` | `/referrals/apply/`    | Apply a referral code    |
| `GET`  | `/referrals/stats/`    | Get referral statistics  |

#### Content (Posts & Comments)

| Method      | Endpoint                               | Description      |
| ----------- | -------------------------------------- | ---------------- |
| `POST`      | `/content/posts/create/`               | Create a post    |
| `GET`       | `/content/posts/list/`                 | List posts       |
| `PUT/PATCH` | `/content/posts/<id>/update/`          | Update a post    |
| `DELETE`    | `/content/posts/<id>/delete/`          | Delete a post    |
| `POST`      | `/content/posts/<id>/comments/create/` | Add a comment    |
| `GET`       | `/content/posts/<id>/comments/list/`   | List comments    |
| `DELETE`    | `/content/comments/<id>/delete/`       | Delete a comment |

#### Payments & Billing

| Method | Endpoint                     | Description          |
| ------ | ---------------------------- | -------------------- |
| `GET`  | `/payments/`                 | List user's payments |
| `GET`  | `/payments/billing/history/` | Billing history      |

---

### Admin APIs

**Base path:** `/api/admin/` — Requires admin/superuser role.

#### User Management

| Method      | Endpoint                | Description            |
| ----------- | ----------------------- | ---------------------- |
| `GET`       | `/users/`               | List users (paginated) |
| `GET`       | `/all-users/`           | Get all users          |
| `PUT/PATCH` | `/users/<id>/edit-user` | Edit user details      |
| `GET`       | `/payments/`            | List all payments      |

#### Dashboard & Analytics

| Method | Endpoint                | Description              |
| ------ | ----------------------- | ------------------------ |
| `GET`  | `/dashboard/stats/`     | System dashboard stats   |
| `GET`  | `/analytics/dashboard/` | Analytics dashboard data |

#### Subscription Management

| Method      | Endpoint                          | Description                 |
| ----------- | --------------------------------- | --------------------------- |
| `POST`      | `/subscriptions/create/`          | Create subscription         |
| `GET`       | `/subscriptions/list/`            | List all subscriptions      |
| `PUT/PATCH` | `/subscriptions/<id>/update/`     | Update subscription         |
| `DELETE`    | `/subscriptions/<id>/delete/`     | Delete subscription         |
| `GET`       | `/subscriptions/analytics/`       | Subscription analytics      |
| `GET`       | `/subscriptions/dashboard/`       | Subscription dashboard      |
| `POST`      | `/subscriptions/<id>/renew/`      | Renew specific subscription |
| `POST`      | `/subscriptions/sync/auto-renew/` | Trigger auto-renewal batch  |

#### Subscription Plan Management

| Method      | Endpoint                          | Description             |
| ----------- | --------------------------------- | ----------------------- |
| `GET`       | `/subscriptionplans/list/`        | List all plans          |
| `POST`      | `/subscriptionplans/create/`      | Create a plan           |
| `PUT/PATCH` | `/subscriptionplans/<id>/update/` | Update a plan           |
| `DELETE`    | `/subscriptionplans/<id>/delete/` | Delete a plan           |
| `GET`       | `/subscriptionplans/analytics/`   | Plan analytics          |
| `GET`       | `/subscriptionplans/dashboard/`   | Plan dashboard overview |

#### Content Moderation

| Method | Endpoint               | Description               |
| ------ | ---------------------- | ------------------------- |
| `GET`  | `/moderation/queue/`   | View moderation queue     |
| `POST` | `/moderation/action/`  | Take moderation action    |
| `GET`  | `/moderation/history/` | Moderation action history |
| `POST` | `/moderation/appeal/`  | Submit moderation appeal  |

---

### Payment APIs

**Base path:** `/api/payment/`

| Method | Endpoint               | Description              | Auth                 |
| ------ | ---------------------- | ------------------------ | -------------------- |
| `POST` | `/create-intent/`      | Create payment intent    | Yes                  |
| `POST` | `/confirm/`            | Confirm a payment        | Yes                  |
| `GET`  | `/status/`             | Get payment status       | Yes                  |
| `POST` | `/refund/`             | Request a refund         | Yes                  |
| `GET`  | `/providers/`          | List available providers | Yes                  |
| `POST` | `/webhook/<provider>/` | Webhook callback         | No (provider-signed) |

---

## Services

The service layer contains all business logic, keeping API views thin.

| Service                 | Description                                                                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **SubscriptionService** | Subscription lifecycle — get/create, validate, check limits, change plans, renew, cancel, extend. Generic feature flag checks via `can_use_feature()`.     |
| **PaymentService**      | Payment orchestrator — coordinates coupon validation → discounted price → payment intent → coupon usage → referral rewards in a single atomic transaction. |
| **RefundService**       | Processes full/partial refunds via payment provider, updates payment status.                                                                               |
| **DiscountService**     | Coupon validation and application — percentage and fixed discounts, per-user limits, expiration checks.                                                    |
| **ReferralService**     | Referral code generation, application, reward distribution, stats tracking.                                                                                |
| **NotificationService** | Multi-channel notification sending — email (SendGrid), SMS (Twilio), push (Firebase).                                                                      |
| **AnalyticsService**    | Monthly data aggregation (MRR, active subscribers, churn) and dashboard stats.                                                                             |
| **ModerationService**   | Content moderation queue, approval/rejection, appeal handling, auto-moderation rules.                                                                      |

---

## Models

### Core Models

| Model              | Description                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| `User`             | Custom user extending `AbstractBaseUser` with `email` as username, `role`, `preferred_language`, `fcm_token` |
| `SubscriptionPlan` | Plan definition with pricing, limits, and feature details                                                    |
| `Subscription`     | User↔Plan binding with billing frequency, dates, auto-renew, status                                          |
| `Payment`          | Payment records with status tracking, provider info                                                          |
| `Renewal`          | Subscription renewal history                                                                                 |
| `Event`            | Calendar events (Action/Reminder types, recurrence support)                                                  |
| `Reminder`         | Standalone time-based reminders                                                                              |
| `Notification`     | In-app notifications (Expiry/Renewal/System types)                                                           |
| `FeatureFlags`     | JSON-based feature configuration per plan (OneToOne with SubscriptionPlan)                                   |
| `MonthlyAnalytics` | Aggregated monthly business metrics                                                                          |

### Content & Moderation Models

| Model              | Description                                   |
| ------------------ | --------------------------------------------- |
| `Post`             | User-generated content with moderation status |
| `Comment`          | Comments on posts                             |
| `ModerationQueue`  | Content awaiting moderation review            |
| `ModerationAppeal` | User appeals against moderation decisions     |

### Discount & Referral Models

| Model                 | Description                                                   |
| --------------------- | ------------------------------------------------------------- |
| `Coupon`              | Discount coupons (percentage/fixed, expiration, usage limits) |
| `CouponUsage`         | Per-user coupon usage tracking                                |
| `ReferralCode`        | User referral codes with reward configuration                 |
| `ReferralTransaction` | Referral usage and reward history                             |

### Logging Models

| Model         | Description            |
| ------------- | ---------------------- |
| `ActivityLog` | User activity tracking |
| `AuditLog`    | System audit trail     |

### Enums / Choices

| Enum                 | Values                                                                   |
| -------------------- | ------------------------------------------------------------------------ |
| `BillingFrequency`   | Monthly, Yearly, Weekly, Quarterly, Semi-Annually, One-Time              |
| `SubscriptionStatus` | Active, Expired, Cancelled, Pending, Suspended, RenewalPending, Trial    |
| `PaymentStatus`      | Pending, Processing, Completed, Failed, Cancelled, Refunded, Partial     |
| `PaymentMethod`      | CreditCard, DebitCard, PayPal, BankTransfer, Crypto, ApplePay, GooglePay |
| `NotificationType`   | Expiry, Renewal, System                                                  |
| `EventType`          | Action, Reminder                                                         |
| `EventCategory`      | Personal, Work, Birthday, Deadline, Other                                |
| `ModerationStatus`   | pending, approved, rejected, deleted, changes_requested                  |
| `DiscountType`       | percentage, fixed                                                        |
| `ReferralRewardType` | credit, discount, free_month, feature_unlock                             |

---

## Middleware

Custom middleware defined in `myapp/middleware.py`, applied in order:

| Middleware                      | Purpose                                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **RequestLoggingMiddleware**    | Logs all HTTP requests with method, path, status, duration, user context, and client IP. Outputs structured JSON in production.       |
| **APIRateLimitMiddleware**      | Enforces subscription-based rate limits on `/api/core/*` endpoints. Returns HTTP 429 when quota exceeded.                             |
| **LanguageMiddleware**          | Activates i18n language based on: (1) `Accept-Language` header, (2) `user.preferred_language`, (3) `settings.LANGUAGE_CODE` fallback. |
| **JWTAuthenticationMiddleware** | Validates JWT tokens and attaches `request.user`, `request.user_id`, and `request.role` for downstream use.                           |

---

## Payment System

The payment system uses the **Strategy Pattern** for provider-agnostic payment processing.

### Providers

| Provider      | Class                         | Status     |
| ------------- | ----------------------------- | ---------- |
| Stripe        | `StripePaymentProvider`       | Production |
| PayPal        | `PayPalPaymentProvider`       | Production |
| Bank Transfer | `BankTransferPaymentProvider` | Production |
| Apple IAP     | `AppleIAPProvider`            | Available  |
| Google Play   | `GooglePlayProvider`          | Available  |

### Usage

```python
from myapp.payment_strategies.factory import get_payment_manager

manager = get_payment_manager()

# Create a payment
result = manager.create_payment(
    amount=Decimal("29.99"),
    currency="USD",
    provider="stripe",
    description="Pro Plan - Monthly",
    metadata={"user_id": "123"}
)

if result.success:
    print(f"Transaction: {result.transaction_id}")
```

### Webhook Handling

Webhooks are processed via `POST /api/payment/webhook/<provider>/`. Supported events:

**Stripe:**

- `payment_intent.succeeded` — Marks payment as completed
- `payment_intent.payment_failed` — Records payment failure
- `invoice.paid` — Renews subscription
- `invoice.payment_failed` — Suspends subscription
- `customer.subscription.created/updated/deleted` — Syncs subscription status

**PayPal:**

- `PAYMENT.CAPTURE.COMPLETED/DENIED`
- `BILLING.SUBSCRIPTION.CREATED/ACTIVATED/CANCELLED`
- `PAYMENT.SALE.COMPLETED`

---

## Feature Flags

The system uses a generic, JSON-based feature flag system via the `FeatureFlags` model (OneToOne with `SubscriptionPlan`).

### Configuration

```python
# Create feature flags for a plan
from myapp.models.features import FeatureFlags

FeatureFlags.objects.create(
    subscription_plan=pro_plan,
    features={
        "api_access": {"enabled": True, "calls_per_hour": 5000},
        "ai_analytics": {"enabled": True, "limit": 1000},
        "advanced_analytics": {"enabled": True},
        "real_time_data": {"enabled": True},
        "export_formats": {"csv": True, "pdf": True, "excel": True},
        "team_collaboration": {"enabled": True, "max_members": 10},
        "custom_reports": {"enabled": True, "max_per_month": 50},
        "integrations": {"slack": True, "webhook": True},
    }
)
```

### Checking Features

```python
from myapp.services.subscription_service import SubscriptionService
from myapp.models.features import FeatureDefinition

# Check if user can access a feature
can_use, message = SubscriptionService.can_use_feature(
    user, FeatureDefinition.API_ENABLED
)

# Get all features for a user
features = SubscriptionService.get_subscription_features(user)
```

### Available Feature Paths (FeatureDefinition)

| Constant                     | Path                         | Description           |
| ---------------------------- | ---------------------------- | --------------------- |
| `API_ENABLED`                | `api_access.enabled`         | API access toggle     |
| `API_CALLS_PER_HOUR`         | `api_access.calls_per_hour`  | Hourly rate limit     |
| `API_DAILY_LIMIT`            | `api_access.daily_limit`     | Daily operation quota |
| `AI_ANALYTICS_ENABLED`       | `ai_analytics.enabled`       | AI analytics feature  |
| `ADVANCED_ANALYTICS_ENABLED` | `advanced_analytics.enabled` | Advanced analytics    |
| `REAL_TIME_DATA_ENABLED`     | `real_time_data.enabled`     | Real-time data        |
| `WEBHOOK_ENABLED`            | `integrations.webhook`       | Webhook integration   |
| `EXPORT_CSV`                 | `export_formats.csv`         | CSV export            |
| `EXPORT_PDF`                 | `export_formats.pdf`         | PDF export            |
| `EXPORT_EXCEL`               | `export_formats.excel`       | Excel export          |

---

## Celery Tasks

Async tasks powered by Celery with RabbitMQ broker and Redis result backend.

### Tasks

| Task                               | Schedule  | Description                                                        |
| ---------------------------------- | --------- | ------------------------------------------------------------------ |
| `send_notification_task`           | On-demand | Sends notifications via email/SMS/push. Retries 3x with 60s delay. |
| `auto_renew_subscriptions_task`    | Periodic  | Finds and renews subscriptions expiring within 24 hours.           |
| `aggregate_monthly_analytics_task` | Periodic  | Aggregates monthly metrics (MRR, subscribers, churn).              |
| `cleanup_old_records_task`         | Periodic  | Permanently deletes soft-deleted records older than 90 days.       |
| `send_event_reminders_task`        | Periodic  | Sends notification emails for reminders due within 24 hours.       |

### Running Celery

```bash
cd src

# Start worker
celery -A configuration worker --loglevel=info --concurrency=4

# Start beat scheduler (for periodic tasks)
celery -A configuration beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Monitor with Flower (optional)
celery -A configuration flower --port=5555
```

Or via Makefile:

```bash
make celery-worker
make celery-beat
make celery-flower
```

---

## Notifications

Multi-channel notification system supporting:

| Channel | Provider       | Configuration                                 |
| ------- | -------------- | --------------------------------------------- |
| Email   | SendGrid       | `EMAIL_HOST_*` env vars or `SENDGRID_API_KEY` |
| SMS     | Twilio         | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`     |
| Push    | Firebase Admin | `FIREBASE_CREDENTIALS` JSON                   |

### Sending Notifications

```python
# Synchronous
from myapp.services.notification_service import NotificationService
service = NotificationService()
service.send_notification(user=user, title="Welcome!", message="...", channels=["email"])

# Asynchronous (via Celery)
from myapp.tasks.tasks import send_notification_task
send_notification_task.delay(user_id=1, title="Alert", message="...", channels=["email", "push"])
```

---

## Internationalization (i18n)

The system supports multi-language responses:

- **Supported languages** (configurable in `settings/base.py`): English (`en`), Spanish (`es`)
- **Language detection order**: `Accept-Language` header → `user.preferred_language` → `settings.LANGUAGE_CODE`
- **Translation files**: `src/locale/<lang>/LC_MESSAGES/`

### Adding a New Language

1. Add to `LANGUAGES` in `settings/base.py`:
   ```python
   LANGUAGES = [
       ("en", "English"),
       ("es", "Spanish"),
       ("fr", "French"),  # New
   ]
   ```
2. Generate translation files:
   ```bash
   cd src && python manage.py makemessages -l fr
   ```
3. Edit `locale/fr/LC_MESSAGES/django.po` with translations
4. Compile:
   ```bash
   python manage.py compilemessages
   ```

---

## Testing

Tests use **pytest** with **pytest-django**. Configuration is in `pytest.ini`.

### Running Tests

```bash
# All tests
cd template-backend
python -m pytest src/tests/ tests/ --create-db --tb=short -q

# Without coverage (faster)
python -m pytest src/tests/ tests/ --create-db --no-cov --tb=short -q

# Specific test file
python -m pytest src/tests/test_services.py -q

# Specific test class
python -m pytest src/tests/test_api.py::TestAuthAPI -q

# Only unit tests
python -m pytest src/tests/ -m unit -q

# With coverage report
python -m pytest src/tests/ tests/ --create-db --cov=src/myapp --cov-report=html
```

Or via Makefile:

```bash
make test           # Run all tests
make test-cov       # With coverage
make test-unit      # Unit tests only
make test-failed    # Re-run failed
```

### Test Structure

| File                 | Coverage                                                                                                 |
| -------------------- | -------------------------------------------------------------------------------------------------------- |
| `conftest.py`        | Shared fixtures (users, subscriptions, payments, coupons, etc.)                                          |
| `test_api.py`        | API integration tests for auth, core, admin, payment endpoints                                           |
| `test_services.py`   | Unit tests for all services (Payment, Refund, Subscription, Discount, Referral, Analytics, Notification) |
| `test_middleware.py` | Middleware tests (JWT, rate limiting, logging, i18n)                                                     |
| `test_tasks.py`      | Celery task tests (all 5 tasks)                                                                          |
| `test_webhooks.py`   | Stripe & PayPal webhook handler tests                                                                    |
| `test_models.py`     | Model validation and method tests                                                                        |
| `test_basic.py`      | Smoke tests (settings, imports)                                                                          |

### Test Configuration

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = configuration.settings
django_find_django = false
python_files = test_*.py
python_classes = Test*
python_functions = test_*
testpaths = src
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
addopts = --reuse-db --nomigrations --tb=short --strict-markers
```

### Coverage Target

Minimum coverage threshold: **70%** (configured via `--cov-fail-under=70`).

---

## Code Quality

### Linting & Formatting

The project uses **Ruff** for both linting and formatting:

```bash
# Lint
make lint           # Check for issues
make lint-fix       # Auto-fix issues

# Format
make format         # Format code
make format-check   # Check formatting without changes
```

### Pre-commit Hooks

```bash
# Install hooks
make install-pre-commit

# Run manually
make pre-commit
```

Configuration is in `.pre-commit-config.yaml`.

---

## Deployment

### Production Checklist

1. Set `DJANGO_ENV=production` and `DEBUG=False`
2. Generate strong `SECRET_KEY` and `JWT_SIGNING_KEY`
3. Configure PostgreSQL with connection pooling
4. Set up Redis for cache + Celery results
5. Set up RabbitMQ for Celery broker
6. Configure Stripe keys (production mode)
7. Set `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
8. Run `python manage.py collectstatic`
9. Run `python manage.py migrate`
10. Start Gunicorn, Celery worker, Celery beat

### Production Commands

```bash
# Gunicorn (4 workers, gevent)
gunicorn configuration.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class gevent \
  --timeout 120

# Celery worker
celery -A configuration worker --loglevel=warning --concurrency=4

# Celery beat
celery -A configuration beat --loglevel=warning \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Docker Production

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Health Checks

- **Application**: `GET /swagger/` — returns 200 with Swagger UI
- **Database**: Checked automatically by Django on startup
- **Redis**: `redis-cli -a $REDIS_PASSWORD ping`
- **RabbitMQ**: `rabbitmq-diagnostics ping`

---

## Makefile Commands

| Command                 | Description                                    |
| ----------------------- | ---------------------------------------------- |
| `make help`             | Show all available targets                     |
| **Setup**               |                                                |
| `make install`          | Install production dependencies                |
| `make install-dev`      | Install all dependencies (including dev)       |
| **Django**              |                                                |
| `make run`              | Start development server                       |
| `make migrate`          | Apply database migrations                      |
| `make makemigrations`   | Generate migrations from model changes         |
| `make createsuperuser`  | Create admin user                              |
| `make collectstatic`    | Collect static files                           |
| `make shell`            | Open Django shell                              |
| `make shell-plus`       | Open enhanced Django shell (django-extensions) |
| **Testing**             |                                                |
| `make test`             | Run all tests                                  |
| `make test-cov`         | Run with coverage report                       |
| `make test-unit`        | Run unit tests only                            |
| `make test-integration` | Run integration tests only                     |
| **Code Quality**        |                                                |
| `make lint`             | Run Ruff linter                                |
| `make lint-fix`         | Auto-fix lint issues                           |
| `make format`           | Format code with Ruff                          |
| `make check`            | Run all checks (lint + format + Django check)  |
| **Celery**              |                                                |
| `make celery-worker`    | Start Celery worker                            |
| `make celery-beat`      | Start Celery beat scheduler                    |
| `make celery-flower`    | Start Flower monitoring UI                     |
| **Docker**              |                                                |
| `make docker-up`        | Start Docker services                          |
| `make docker-down`      | Stop Docker services                           |
| `make docker-build`     | Build Docker image                             |
| `make docker-logs`      | View Docker logs                               |
| **Cleanup**             |                                                |
| `make clean`            | Remove temp files and caches                   |
| `make clean-all`        | Full cleanup (including DB)                    |
| `make clean-pyc`        | Remove `.pyc` and `__pycache__`                |

---

## Troubleshooting

### Common Issues

**`ImportError: cannot import name 'PaymentMethod'`**
Clear Python cache and restart:

```bash
# Linux/Mac
find src -type d -name __pycache__ -exec rm -rf {} +
# Windows (PowerShell)
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -Path src | Remove-Item -Recurse -Force
```

**`[Django] Using DEVELOPMENT settings` appears twice**
Normal behavior — Django's `runserver` spawns a reloader process. The second message is suppressed by default. If it appears twice, ensure `settings/__init__.py` has the `RUN_MAIN` check.

**Database connection refused**
Ensure Docker services are running:

```bash
docker-compose up -d
docker-compose ps  # Verify all services are "Up"
```

**Celery tasks not executing**

1. Verify RabbitMQ is running: `docker-compose ps rabbitmq`
2. Start a Celery worker: `make celery-worker`
3. Check broker URL in settings matches your `.env`

**Tests failing with `django.db.utils.OperationalError`**
Use `--create-db` to force recreate the test database:

```bash
python -m pytest src/tests/ --create-db -q
```

**Rate limiting returning 429 on all requests**
Check that the user has an active subscription with a plan that has feature flags configured. Create feature flags for the plan if missing.

---
