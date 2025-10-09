#!/usr/bin/env sh
# Entrypoint for the web container.
# - Ensures static directory exists and is writable
# - Optionally runs migrations when AUTO_MIGRATE=1|true
# - Always collects static files
# - Starts the provided command (Gunicorn) as the 'sage' user
set -e

mkdir -p /app/staticfiles
chown -R sage:sage /app/staticfiles || true

# Optional: run migrations when AUTO_MIGRATE=1 or "true"
if [ "${AUTO_MIGRATE:-0}" = "1" ] || [ "${AUTO_MIGRATE:-false}" = "true" ]; then
  echo "Running migrations..."
  su -s /bin/sh -c "sage -python manage.py migrate --noinput" sage
fi

echo "Collecting static files..."
su -s /bin/sh -c "sage -python manage.py collectstatic --noinput" sage

echo "Starting web server as 'sage': $*"
exec su -s /bin/sh -c "$*" sage

