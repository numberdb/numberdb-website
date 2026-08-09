#!/usr/bin/env sh
# Entrypoint for the web container.
# - Ensures static directory exists and is writable
# - Optionally runs migrations when AUTO_MIGRATE=1|true
# - Always collects static files
# - Starts the provided command (Gunicorn) as the 'sage' user
set -e

mkdir -p /app/staticfiles
chown -R sage:sage /app/staticfiles || true

run_as_sage() {
  if command -v gosu >/dev/null 2>&1; then
    gosu sage "$@"
  else
    # Fallback (does not preserve complex quoting); prefer installing gosu.
    su -s /bin/sh -c "$*" sage
  fi
}

# Optional: run migrations when AUTO_MIGRATE=1 or "true"
if [ "${AUTO_MIGRATE:-0}" = "1" ] || [ "${AUTO_MIGRATE:-false}" = "true" ]; then
  echo "Running migrations..."
  run_as_sage sage -python manage.py migrate --noinput
fi

echo "Collecting static files..."
run_as_sage sage -python manage.py collectstatic --noinput

echo "Starting command as 'sage': $*"
if command -v gosu >/dev/null 2>&1; then
  exec gosu sage "$@"
fi
exec su -s /bin/sh -c "$*" sage
