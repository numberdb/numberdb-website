#!/usr/bin/env sh
set -e

# Optional: run migrations when AUTO_MIGRATE=1
if [ "${AUTO_MIGRATE:-0}" = "1" ] || [ "${AUTO_MIGRATE:-false}" = "true" ]; then
  echo "Running migrations..."
  sage -python manage.py migrate --noinput
fi

echo "Collecting static files..."
sage -python manage.py collectstatic --noinput

echo "Starting web server: $*"
exec "$@"

