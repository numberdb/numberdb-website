#!/usr/bin/env bash
set -euo pipefail

# Provision a fresh Ubuntu LTS VM (no DNS) and deploy this app over HTTP.
#
# Usage:
#   scripts/provision_vm.sh [--force-secrets] [--no-build] [--no-wiki] [--no-oeis] user@host [/remote/path]
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
BUILD_DATA=1
WITH_WIKI=1
WITH_OEIS=1
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --force-secrets) FORCE_SECRETS=1 ;;
    --no-build) BUILD_DATA=0 ;;
    --no-wiki) WITH_WIKI=0 ;;
    --no-oeis) WITH_OEIS=0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

REMOTE=${1:-}
REMOTE_PATH=${2:-/opt/numberdb-website}

if [[ -z "$REMOTE" ]]; then
  echo "Usage: $0 [--force-secrets] user@host [/remote/path]" >&2
  exit 1
fi
if [[ -z "$REMOTE_PATH" ]]; then
  echo "Error: REMOTE_PATH resolved empty. Pass it explicitly as the second positional arg." >&2
  exit 2
fi

# Extract IP/host for ALLOWED_HOSTS/SERVER_NAME (best effort)
REMOTE_ALIAS=${REMOTE#*@}
REMOTE_HOST=$(
  ssh -G "$REMOTE" 2>/dev/null | awk '/^hostname /{print $2; exit}'
)
if [[ -z "$REMOTE_HOST" ]]; then
  REMOTE_HOST="$REMOTE_ALIAS"
fi

# Generate secrets locally (used only on first create or when forcing)
rand_hex() { openssl rand -hex "$1"; }
rand_pw()  { openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24; }

SECRET_KEY=$(rand_hex 32)
POSTGRES_KEY=$(rand_hex 16)
ADMIN_PASSWORD=$(rand_pw)
LETSENCRYPT_EMAIL="admin@example.invalid"

SSH_OPTS=(-o ExitOnForwardFailure=no -o StrictHostKeyChecking=accept-new)

echo "==> Installing Docker on remote host ($REMOTE)"
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
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
  mkdir -p '$REMOTE_PATH'; \
"

echo "==> Hardening SSH on remote host"
# A fresh VM is on the public internet with no firewall, and sshd is the only
# service on it that accepts credentials. Note that a firewall would not
# substitute for binding container ports to loopback: Docker publishes ports
# through its own iptables chain and bypasses ufw rules entirely.
#
# Guarded on authorized_keys existing -- disabling password auth on a VM the
# operator reaches *by password* would lock them out of their own box.
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -s <<'EOS'
set -euo pipefail
if [ -s "$HOME/.ssh/authorized_keys" ]; then
  install -d -m 0755 /etc/ssh/sshd_config.d
  cat > /etc/ssh/sshd_config.d/99-hardening.conf <<'CONF'
# Written by scripts/provision_vm.sh
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
CONF
  if sshd -t; then
    systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
    echo "    SSH hardened: password auth disabled, root key-only"
  else
    rm -f /etc/ssh/sshd_config.d/99-hardening.conf
    echo "    WARN: sshd config invalid, hardening skipped" >&2
  fi
else
  echo "    WARN: no authorized_keys found; leaving password auth enabled to avoid lockout" >&2
fi
EOS

# docker-compose.override.yml is excluded deliberately, not merely as noise.
# Compose loads it automatically, so shipping a developer's copy would silently
# reconfigure production -- the local one runs Django's dev server with DEBUG on
# and publishes nothing but 127.0.0.1. It is also the filename this script's own
# staging step writes on the remote, so a copied file would fight with it.
echo "==> Copying repository to $REMOTE:$REMOTE_PATH (excluding .git, caches, local envs)"
REPO_ROOT=$(pwd)
tar cz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='staticfiles' \
  --exclude='data_pipeline/oeis-data' \
  --exclude='.env' \
  --exclude='.env.prod' \
  --exclude='docker-compose.override.yml' \
  -C "$REPO_ROOT" . | ssh "${SSH_OPTS[@]}" "$REMOTE" "tar xz -C '$REMOTE_PATH'"

echo "==> Writing .env.prod on remote (force: $FORCE_SECRETS); syncing to .env if missing"
if [[ "$FORCE_SECRETS" -eq 1 ]]; then
  ssh "${SSH_OPTS[@]}" "$REMOTE" "bash -lc 'set -e; cd \"$REMOTE_PATH\"; cat > .env.prod'" << EOFENV
SECRET_KEY=$SECRET_KEY
POSTGRES_KEY=$POSTGRES_KEY
DEBUG=False
ALLOWED_HOSTS=.localhost,127.0.0.1,$REMOTE_HOST,$REMOTE_ALIAS

# Compose overrides this for the web container to point to 'db'
DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb

# Web server tuning
GUNICORN_WORKERS=1

# Postgres performance tuning (low-RAM profile)
PG_SHARED_BUFFERS=128MB
PG_WORK_MEM=16MB
PG_MAINTENANCE_WORK_MEM=128MB
PG_EFFECTIVE_CACHE_SIZE=512MB
PG_WAL_COMPRESSION=on
PG_SYNCHRONOUS_COMMIT=off
PG_MAX_WAL_SIZE=512MB
PG_CHECKPOINT_TIMEOUT=10min

SOCIALACCOUNT_GITHUB_ID=
SOCIALACCOUNT_GITHUB_SECRET=

ACCOUNT_DEFAULT_HTTP_PROTOCOL=http
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# TLS vars (not used until DNS is set)
SERVER_NAME=$REMOTE_HOST
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
EOFENV
else
  ssh "${SSH_OPTS[@]}" "$REMOTE" "bash -lc 'set -e; cd \"$REMOTE_PATH\"; test -f .env.prod || cat > .env.prod'" << EOFENV
SECRET_KEY=$SECRET_KEY
POSTGRES_KEY=$POSTGRES_KEY
DEBUG=False
ALLOWED_HOSTS=.localhost,127.0.0.1,$REMOTE_HOST,$REMOTE_ALIAS

# Compose overrides this for the web container to point to 'db'
DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb

# Web server tuning
GUNICORN_WORKERS=1

# Postgres performance tuning (low-RAM profile)
PG_SHARED_BUFFERS=128MB
PG_WORK_MEM=16MB
PG_MAINTENANCE_WORK_MEM=128MB
PG_EFFECTIVE_CACHE_SIZE=512MB
PG_WAL_COMPRESSION=on
PG_SYNCHRONOUS_COMMIT=off
PG_MAX_WAL_SIZE=512MB
PG_CHECKPOINT_TIMEOUT=10min

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
  ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "set -e; cd '$REMOTE_PATH'; cp .env.prod .env"
else
  ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "set -e; cd '$REMOTE_PATH'; [ -f .env ] || cp .env.prod .env"
fi

echo "==> Building and starting containers (HTTP only; no DNS)"
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose up -d --build db pyro-ns eval web nginx certbot-renew; \
"

# Full history, not --depth 1: the builder derives contributors and table
# histories from the commit log, and a shallow clone has exactly one commit.
echo "==> Fetching numberdb-data"
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm data-fetcher || \
    docker run --rm -v numberdb-website_numberdb-data:/numberdb-data alpine/git:latest clone https://github.com/numberdb/numberdb-data.git /numberdb-data || \
    docker run --rm -v numberdb-website_numberdb-data:/numberdb-data alpine/git:latest -C /numberdb-data pull; \
"

echo "==> Applying database migrations"
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm web sage -python manage.py migrate; \
"

echo "==> Creating admin user (username: admin)"
ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
  set -e; cd '$REMOTE_PATH'; \
  docker compose run --rm web bash -lc \"set -e; cat > /tmp/create_admin.py << 'PY'\\nfrom django.contrib.auth import get_user_model\\nUser = get_user_model()\\nif not User.objects.filter(username='admin').exists():\\n    User.objects.create_superuser('admin','admin@example.org','${ADMIN_PASSWORD}')\\n    print('Created admin user.')\\nelse:\\n    print('Admin user already exists.')\\nPY\\n  ; sage -python manage.py shell < /tmp/create_admin.py\"; \
"

echo "==> Done. App is up over HTTP at: http://$REMOTE_HOST"
echo "    Admin credentials: admin / $ADMIN_PASSWORD"
echo "    When DNS points to the server, obtain TLS with:"
echo "      ssh $REMOTE 'cd $REMOTE_PATH && docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d \$SERVER_NAME --email \$LETSENCRYPT_EMAIL --agree-tos --no-eff-email && docker compose restart nginx'"

# Optional dataset builds
if [[ "$BUILD_DATA" -eq 1 ]]; then
  echo "==> Building NumberDB data in background (tables, numbers, search). Logs: logs/build_core.log"
  ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
    set -e; cd '$REMOTE_PATH'; mkdir -p logs; \
    nohup sh -lc 'docker compose run -T --rm web sage -python data_pipeline/build.py > logs/build_core.log 2>&1' >/dev/null 2>&1 & \
  "
else
  echo "==> Skipping NumberDB core build (requested)"
fi

if [[ "$WITH_WIKI" -eq 1 ]]; then
  echo "==> Building Wikipedia tables in background. Logs: logs/build_wikipedia.log"
  ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
    set -e; cd '$REMOTE_PATH'; mkdir -p logs; \
    nohup sh -lc 'docker compose run -T --rm web sage -python data_pipeline/build-wikipedia.py > logs/build_wikipedia.log 2>&1' >/dev/null 2>&1 & \
  "
else
  echo "==> Skipping Wikipedia build (requested)"
fi

if [[ "$WITH_OEIS" -eq 1 ]]; then
  echo "==> Building OEIS tables in background. Logs: logs/build_oeis.log"
  ssh "${SSH_OPTS[@]}" "$REMOTE" bash -lc "\
    set -e; cd '$REMOTE_PATH'; mkdir -p logs; \
    nohup sh -lc 'docker compose run -T --rm web sh -lc \''./data_pipeline/update-oeis.sh && sage -python data_pipeline/build-oeis.py'\'' > logs/build_oeis.log 2>&1' >/dev/null 2>&1 & \
  "
else
  echo "==> Skipping OEIS build (requested)"
fi

echo "==> To monitor builds on the server:"
echo "    tail -f /opt/numberdb-website/logs/build_core.log"
echo "    tail -f /opt/numberdb-website/logs/build_wikipedia.log"
echo "    tail -f /opt/numberdb-website/logs/build_oeis.log"
