#!/usr/bin/env bash
set -o errexit

mkdir -p media

python manage.py migrate --no-input

if [ "${CREATE_GESTOR:-1}" = "1" ]; then
  python manage.py criar_gestor || true
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
