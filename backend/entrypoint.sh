#!/bin/sh
# Release step first (migrations run before new code takes traffic), then serve.
set -e
python manage.py migrate --noinput
exec gunicorn config.wsgi -b 0.0.0.0:8000 --workers 2 --access-logfile -
