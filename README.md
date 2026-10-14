# Transactions API

Django 5.2 + DRF + Postgres 16 backend API. JWT auth, Sentry (optional), pytest, Docker
Compose, GitHub Actions CI (Bitbucket Pipelines mirror).

## Run it (Docker)

```bash
cp .env.example .env
docker compose up --build    # http://localhost:8000/api/docs/
```

The `api` container runs migrations on start, then serves via gunicorn on port 8000.
Health check: `curl localhost:8000/api/health/`.

## Local development

```bash
cp .env.example .env
make up          # postgres only, in docker
make install     # venv + pip + git hooks
make migrate
make run-api     # http://localhost:8000/api/docs/
make test lint   # pytest + missing-migrations check, ruff
```

Auth: `POST /api/auth/token/` with `{"username", "password"}` returns `{access, refresh}`; send
`Authorization: Bearer <access>`. Create a user: `cd backend && .venv/bin/python manage.py createsuperuser`
(or `docker compose exec api python manage.py createsuperuser`).

Engineering standards (workflow, AI roles, migration policy, code rules): see `AGENTS.md`.
Every change lands via PR; CI must be green to merge.
