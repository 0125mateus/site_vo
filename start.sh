#!/usr/bin/env bash
set -o errexit

mkdir -p media

python manage.py migrate --no-input

if [ "${CREATE_GESTOR:-1}" = "1" ]; then
  if [ -n "${GESTOR_PASSWORD:-}" ]; then
    python manage.py criar_gestor --password "$GESTOR_PASSWORD" || true
  else
    python manage.py criar_gestor || true
  fi
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --timeout 120 --workers 1 --threads 4
