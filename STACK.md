# Stack and dependencies

What each piece is and why it's here. Versions are pinned in `backend/requirements*.txt`.

## Infrastructure
| Piece | What it does |
|---|---|
| PostgreSQL 16 (Docker) | The database. Run locally with `make up`; same engine as production |
| Docker Compose | Runs Postgres and the API (`docker compose up --build`), identical on every machine |
| Docker (`backend/Dockerfile`) | Builds the API image: Python 3.12 slim, non-root user, migrates then serves via gunicorn |
| Make | Short commands for common tasks (`make test`, `make lint`, `make run-api`) |
| GitHub Actions | CI: runs lint, tests and the migrations check on every PR; merge gate |
| Bitbucket Pipelines | The same CI, written for Bitbucket (SOUS's CI tool) |
| Git hooks (`.githooks/`) | Pre-commit: lints staged files before each commit |

## Backend (Python)
| Package | What it does |
|---|---|
| Django | Web framework: models (ORM), migrations, admin, settings, security middleware |
| Django REST Framework (DRF) | Builds the JSON API: serializers (validation), viewsets, permissions, pagination, throttling |
| djangorestframework-simplejwt | JWT login: issues access/refresh tokens, authenticates `Authorization: Bearer` requests |
| drf-spectacular | Generates the OpenAPI schema and interactive docs at `/api/docs/` |
| django-environ | Reads config and secrets from environment variables / `.env` |
| django-cors-headers | Lets browser clients on other origins call the API (off unless `CORS_ALLOWED_ORIGINS` is set) |
| psycopg | The Postgres driver Django talks through |
| sentry-sdk | Sends errors and alerts to Sentry (only when `SENTRY_DSN` is set) |
| gunicorn | Production WSGI server that runs Django inside the container |
| anthropic | Official Claude SDK: categorises transactions (`transactions/categorisation.py`); optional at runtime, rules fallback without a key |

## Backend dev tools
| Package | What it does |
|---|---|
| pytest | Test runner |
| pytest-cov | Measures application statement and branch coverage; pytest alone does not report it |
| pytest-django | Lets pytest use Django: test database, `settings` and client fixtures |
| factory_boy | Builds test data (users and app models) with sensible defaults |
| ruff | Linter + formatter for Python (replaces flake8, isort, black) |

## Adding a dependency
Every new package needs a one-line reason in the PR (why not the stdlib or something we already
have), a pinned version, and a row in this file.
