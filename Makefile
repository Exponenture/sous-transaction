PY := backend/.venv/bin/python
MANAGE := cd backend && .venv/bin/python manage.py

.PHONY: up down install hooks migrate migrations run-api test test-api lint fmt shell

up:            ## start postgres (local dev; `docker compose up --build` runs the api too)
	docker compose up -d --wait db

down:
	docker compose down

install:
	test -d backend/.venv || python3 -m venv backend/.venv
	backend/.venv/bin/pip install -q -r backend/requirements-dev.txt
	git config core.hooksPath .githooks

hooks:         ## enable the pre-commit gate (also done by install)
	git config core.hooksPath .githooks

migrate:
	$(MANAGE) migrate

migrations:    ## make migrations after model changes (commit the files)
	$(MANAGE) makemigrations

run-api:
	$(MANAGE) runserver 8000

test: test-api

test-api:      ## pytest + fail on missing migrations
	cd backend && .venv/bin/pytest --create-db  # fresh test DB: stale tables break transactional tests
	cd backend && .venv/bin/python manage.py makemigrations --check --dry-run

lint:
	cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .

fmt:
	cd backend && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

shell:
	$(MANAGE) shell
