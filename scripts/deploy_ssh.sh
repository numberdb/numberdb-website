#!/usr/bin/env bash
set -euo pipefail

# Deploy to a remote Docker host via SSH context using Compose v2.
# Usage:
#   scripts/deploy_ssh.sh ssh://user@host [context-name]
#
# Requirements on your laptop:
# - Docker CLI with Compose v2
# - This repo checked out (on the desired branch, e.g. docker-deploy)
# - A populated .env (contains secrets: SECRET_KEY, POSTGRES_KEY, SERVER_NAME, LETSENCRYPT_EMAIL, etc.)

TARGET=${1:-}
CONTEXT=${2:-prod}

if [[ -z "$TARGET" ]]; then
  echo "Usage: $0 ssh://user@host [context-name]" >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env in repo root. Create it with server/domain secrets." >&2
  exit 1
fi

# Export env from .env so we can use variables below (e.g., SERVER_NAME)
set -a
source ./.env
set +a

if [[ -z "${SERVER_NAME:-}" || -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  echo "SERVER_NAME and LETSENCRYPT_EMAIL must be set in .env" >&2
  exit 1
fi

echo "Ensuring Docker context '$CONTEXT' -> $TARGET"
if ! docker context inspect "$CONTEXT" >/dev/null 2>&1; then
  docker context create "$CONTEXT" --docker "host=$TARGET"
fi

echo "Building images on remote host..."
docker --context "$CONTEXT" compose build

echo "Starting core services..."
docker --context "$CONTEXT" compose up -d db pyro-ns eval web nginx certbot-renew

echo "Fetching/refreshing numberdb-data..."
docker --context "$CONTEXT" compose run --rm data-fetcher || true

echo "Applying database migrations..."
docker --context "$CONTEXT" compose run --rm web sage -python manage.py migrate

echo "Attempting initial TLS issuance for ${SERVER_NAME}..."
set +e
docker --context "$CONTEXT" compose run --rm \
  -e CERTBOT_EMAIL="${LETSENCRYPT_EMAIL}" \
  certbot certonly --webroot -w /var/www/certbot \
  -d "${SERVER_NAME}" --email "${LETSENCRYPT_EMAIL}" --agree-tos --no-eff-email --non-interactive
TLS_STATUS=$?
set -e

if [[ $TLS_STATUS -eq 0 ]]; then
  echo "TLS certificate obtained. Restarting Nginx to enable HTTPS..."
  docker --context "$CONTEXT" compose restart nginx
else
  echo "TLS issuance did not complete (non-fatal). Ensure DNS points to the server and retry:" >&2
  echo "  docker --context $CONTEXT compose run --rm certbot certonly --webroot -w /var/www/certbot -d ${SERVER_NAME} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email" >&2
fi

echo "Done. Site should be reachable at: http://${SERVER_NAME} (and https once cert is active)."

