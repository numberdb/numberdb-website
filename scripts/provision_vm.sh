#!/usr/bin/env bash
set -euo pipefail

# Provision a fresh Ubuntu LTS VM (no DNS) and deploy this app over HTTP.
#
# Usage:
#   scripts/provision_vm.sh [--force-secrets] user@host [/remote/path]
#
# What it does:
# - Installs Docker Engine + Compose plugin on the remote host
# - Copies this repository to the remote path (default: /opt/numberdb-website)
# - Generates repo-root .env.prod with strong secrets and HTTP config (no DNS) — only if missing, unless --force-secrets
# - Copies .env.prod to .env (Compose uses .env) — only if missing, unless --force-secrets
# - Builds images and starts: db, pyro-ns, eval, web, nginx (HTTP), certbot-renew
# - Fetches numberdb-data, runs migrations
# - Creates an admin user with a generated password (printed locally)

FORCE_SECRETS=0
if [[ "${1:-}" == "--force-secrets" ]]; then
  FORCE_SECRETS=1
  shift
fi

REMOTE=${1:-}
REMOTE_PATH=${2:-/opt/numberdb-website}

if [[ -z "$REMOTE" ]]; then
  echo "Usage: $0 [--force-secrets] user@host [/remote/path]" >&2
  exit 1
fi

# Extract IP/host for ALLOWED_HOSTS/SERVER_NAME (best effort)
REMOTE_HOST=${REMOTE#*@}

# Generate secrets locally (used only on first create or when forcing)
rand_hex() { openssl rand -hex "$1"; }
rand_pw()  { openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24; }

SECRET_KEY=$(rand_hex 32)
POSTGRES_KEY=$(rand_hex 16)
ADMIN_PASSWORD=$(rand_pw)
LETSENCRYPT_EMAIL="admin@example.invalid"

echo "==> Installing Docker on remote host ($REMOTE)"
ssh -o StrictHostKeyChecking=accept-new "$REMOTE" bash -lc "\
  set -euo pipefail; \
  export DEBIAN_FRONTEND=noninteractive; \
  apt-get update; \
  apt-get install -y ca-certificates curl gnupg lsb-release; \
  install -m 0755 -d /etc/apt/keyrings; \
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg; \
  chmod a+r /etc/apt/keyrings/docker.gpg; \
  echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \$VERSION_CODENAME) stable\" > /etc/apt/sources.list.d/docker.list; \
  apt-get update; \
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin git; \
  systemctl enable --now docker || true; \
  mkdir -p $REMOTE_PATH; \
"

echo "==> Copying repository to $REMOTE:$REMOTE_PATH (excluding .git, caches, local envs)"
REPO_ROOT=$(pwd)
tar cz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='staticfiles' \
  --exclude='db_builder/oeis-data' \
  --exclude='.env' \
  --exclude='.env.prod' \
  -C "$REPO_ROOT" . | ssh "$REMOTE" "tar xz -C '$REMOTE_PATH'"

echo "==> Writing .env.prod on remote (force: $FORCE_SECRETS); syncing to .env if missing"
if [[ "$FORCE_SECRETS" -eq 1 ]]; then
  ssh "$REMOTE" "bash -lc 'set -e; cd \"$REMOTE_PATH\"; cat > .env.prod'" << EOFENV
SECRET_KEY=$SECRET_KEY
POSTGRES_KEY=$POSTGRES_KEY
DEBUG=False
ALLOWED_HOSTS=.localhost,127.0.0.1,$REMOTE_HOST

# Compose overrides this for the web container to point to 'db'
DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb

SOCIALACCOUNT_GITHUB_ID=
SOCIALACCOUNT_GITHUB_SECRET=

ACCOUNT_DEFAULT_HTTP_PROTOCOL=http
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# TLS vars (not used until DNS is set)
SERVER_NAME=$REMOTE_HOST
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
EOFENV
else
  ssh "$REMOTE" "bash -lc 'set -e; cd \"$REMOTE_PATH\"; test -f .env.prod || cat > .env.prod'" << EOFENV
SECRET_KEY=$SECRET_KEY
POSTGRES_KEY=$POSTGRES_KEY
DEBUG=False
ALLOWED_HOSTS=.localhost,127.0.0.1,$REMOTE_HOST

# Compose overrides this for the web container to point to 'db'
DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb

SOCIALACCOUNT_GITHUB_ID=
SOCIALACCOUNT_GITHUB_SECRET=

ACCOUNT_DEFAULT_HTTP_PROTOCOL=http
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# TLS vars (not used until DNS is set)
SERVER_NAME=$REMOTE_HOST
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
EOFENV
fi

# Only copy .env if missing (or we're forcing)
if [[ "$FORCE_SECRETS" -eq 1 ]]; then
  ssh "$REMOTE" bash -lc "set -e; cd '$REMOTE_PATH'; cp .env.prod .env"
else
  ssh "$REMOTE" bash -lc "set -e; cd '$REMOTE_PATH'; [ -f .env ] || cp .env.prod .env"
fi

echo "==> Building and starting containers (HTTP only; no DNS)"
ssh "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose up -d --build db pyro-ns eval web nginx certbot-renew; \
"

echo "==> Fetching numberdb-data"
ssh "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm data-fetcher || \
    docker run --rm -v numberdb-website_numberdb-data:/numberdb-data alpine/git:latest clone --depth 1 https://github.com/numberdb/numberdb-data.git /numberdb-data || \
    docker run --rm -v numberdb-website_numberdb-data:/numberdb-data alpine/git:latest -C /numberdb-data pull; \
"

echo "==> Applying database migrations"
ssh "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm web sage -python manage.py migrate; \
"

echo "==> Creating admin user (username: admin)"
ssh "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm web bash -lc \"set -e; cat > /tmp/create_admin.py << 'PY'\\nfrom django.contrib.auth import get_user_model\\nUser = get_user_model()\\nif not User.objects.filter(username='admin').exists():\\n    User.objects.create_superuser('admin','admin@example.org','${ADMIN_PASSWORD}')\\n    print('Created admin user.')\\nelse:\\n    print('Admin user already exists.')\\nPY\\n  ; sage -python manage.py shell < /tmp/create_admin.py\"; \
"

echo "==> Done. App is up over HTTP at: http://$REMOTE_HOST"
echo "    Admin credentials: admin / $ADMIN_PASSWORD"
echo "    When DNS points to the server, obtain TLS with:"
echo "      ssh $REMOTE 'cd $REMOTE_PATH && docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d \$SERVER_NAME --email \$LETSENCRYPT_EMAIL --agree-tos --no-eff-email && docker compose restart nginx'"

