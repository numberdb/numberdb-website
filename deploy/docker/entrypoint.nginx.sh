#!/usr/bin/env sh
# Entrypoint for the Nginx container.
# - Requires SERVER_NAME (domain)
# - If Let’s Encrypt certs exist for SERVER_NAME, render TLS template; otherwise HTTP-only
# - Starts Nginx and periodically reloads it (to pick up renewed certs)
set -e

TEMPLATE_HTTP="/etc/nginx/templates/default.conf.http.template"
TEMPLATE_TLS="/etc/nginx/templates/default.conf.tls.template"
OUTPUT_CONF="/etc/nginx/conf.d/default.conf"

mkdir -p /etc/nginx/conf.d

if [ -z "$SERVER_NAME" ]; then
  echo "SERVER_NAME is required (e.g., example.org)."
  exit 1
fi

CERT_FULL="/etc/letsencrypt/live/${SERVER_NAME}/fullchain.pem"
CERT_KEY="/etc/letsencrypt/live/${SERVER_NAME}/privkey.pem"

if [ -f "$CERT_FULL" ] && [ -f "$CERT_KEY" ]; then
  echo "TLS certificate found for ${SERVER_NAME}. Enabling HTTPS."
  envsubst '${SERVER_NAME}' < "$TEMPLATE_TLS" > "$OUTPUT_CONF"
else
  echo "No TLS certificate found. Serving HTTP only."
  envsubst '${SERVER_NAME}' < "$TEMPLATE_HTTP" > "$OUTPUT_CONF"
fi

echo "Starting Nginx..."

# Nginx must be reloaded to pick up renewed cert files. We run a small background
# loop that periodically reloads Nginx (default: every 12 hours).
RELOAD_INTERVAL_SECONDS="${NGINX_RELOAD_INTERVAL_SECONDS:-43200}"
if [ "${RELOAD_INTERVAL_SECONDS}" -gt 0 ] 2>/dev/null; then
  (
    while :; do
      sleep "${RELOAD_INTERVAL_SECONDS}" || exit 0
      echo "Reloading Nginx (certificate refresh)..."
      nginx -s reload || true
    done
  ) &
  RELOADER_PID="$!"
fi

term_handler() {
  echo "Stopping Nginx..."
  if [ -n "${RELOADER_PID:-}" ]; then
    kill "${RELOADER_PID}" 2>/dev/null || true
  fi
  nginx -s quit 2>/dev/null || true
}

trap term_handler INT TERM

nginx -g 'daemon off;'
