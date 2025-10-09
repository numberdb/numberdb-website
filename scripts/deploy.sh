#!/usr/bin/env bash
set -euo pipefail

# One-command remote deploy helper from your laptop.
#
# Actions:
#   stage         -> Provision VM, bind Nginx to localhost:8080, optional tunnel
#   live          -> Set domain/email, issue TLS cert, expose 80/443
#   status        -> Show container status and app URL
#
# Examples:
#   scripts/deploy.sh stage [--force-secrets] [--no-build] [--no-wiki] [--no-oeis] user@host [/remote/path] [--open-tunnel]
#   scripts/deploy.sh live user@host example.org admin@example.org [/remote/path]
#   scripts/deploy.sh status user@host [/remote/path]

ACTION=${1:-}
shift || true

REMOTE_PATH_DEFAULT=/opt/numberdb-website

die() { echo "Error: $*" >&2; exit 2; }

ensure_remote_path() {
  local remote="$1"; local rpath="$2";
  ssh -o StrictHostKeyChecking=accept-new "$remote" bash -lc "mkdir -p '$rpath'"
}

write_override_localbind() {
  local remote="$1"; local rpath="$2"; local port="${3:-8080}";
  local TMPFILE=$(mktemp)
  cat > "$TMPFILE" <<EOF
services:
  nginx:
    ports:
      - "127.0.0.1:${port}:80"
EOF
  scp -q "$TMPFILE" "$remote:$rpath/docker-compose.override.yml"
  rm -f "$TMPFILE"
}

remove_override() {
  local remote="$1"; local rpath="$2";
  ssh "$remote" bash -lc "rm -f '$rpath/docker-compose.override.yml'"
}

set_env_kv() {
  # Usage: set_env_kv remote rpath KEY VALUE
  local remote="$1"; local rpath="$2"; local k="$3"; local v="$4";
  ssh "$remote" bash -lc "cd '$rpath' && sed -i -E '/^${k}=.*/d' .env && echo ${k}=${v} >> .env"
}

open_tunnel_bg() {
  # Usage: open_tunnel_bg user@host [local_port] [remote_port]
  local remote="$1"; local lport="${2:-8080}"; local rport="${3:-8080}";
  ssh -f -N -L "${lport}:127.0.0.1:${rport}" "$remote" || die "Failed to open SSH tunnel"
  echo "Tunnel active: http://localhost:${lport}"
}

case "$ACTION" in
  stage)
    FORCE=0; NO_BUILD=0; NO_WIKI=0; NO_OEIS=0; OPEN_TUNNEL=0
    while [[ "${1:-}" == --* ]]; do
      case "$1" in
        --force-secrets) FORCE=1 ;;
        --no-build) NO_BUILD=1 ;;
        --no-wiki) NO_WIKI=1 ;;
        --no-oeis) NO_OEIS=1 ;;
        --open-tunnel) OPEN_TUNNEL=1 ;;
        *) die "Unknown flag: $1" ;;
      esac; shift
    done
    REMOTE=${1:-}; RPATH=${2:-$REMOTE_PATH_DEFAULT}
    [[ -z "$REMOTE" ]] && die "Usage: scripts/deploy.sh stage [--flags] user@host [/remote/path] [--open-tunnel]"

    ensure_remote_path "$REMOTE" "$RPATH"

    # Build provision flags
    PROV_FLAGS=()
    [[ $FORCE -eq 1 ]] && PROV_FLAGS+=(--force-secrets)
    [[ $NO_BUILD -eq 1 ]] && PROV_FLAGS+=(--no-build)
    [[ $NO_WIKI -eq 1 ]] && PROV_FLAGS+=(--no-wiki)
    [[ $NO_OEIS -eq 1 ]] && PROV_FLAGS+=(--no-oeis)

    # Run provisioner
    scripts/provision_vm.sh ${PROV_FLAGS[@]} "$REMOTE" "$RPATH"

    # Bind Nginx to localhost:8080 on server
    write_override_localbind "$REMOTE" "$RPATH" 8080
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose up -d nginx"
    echo "Nginx bound to 127.0.0.1:8080 on the server."

    if [[ $OPEN_TUNNEL -eq 1 ]]; then
      open_tunnel_bg "$REMOTE" 8080 8080
    else
      echo "Open tunnel manually: ssh -N -L 8080:127.0.0.1:8080 $REMOTE"
    fi
    ;;

  live)
    REMOTE=${1:-}; DOMAIN=${2:-}; EMAIL=${3:-}; RPATH=${4:-$REMOTE_PATH_DEFAULT}
    [[ -z "$REMOTE" || -z "$DOMAIN" || -z "$EMAIL" ]] && die "Usage: scripts/deploy.sh live user@host example.org admin@example.org [/remote/path]"

    ensure_remote_path "$REMOTE" "$RPATH"
    # Set env keys
    set_env_kv "$REMOTE" "$RPATH" SERVER_NAME "$DOMAIN"
    set_env_kv "$REMOTE" "$RPATH" LETSENCRYPT_EMAIL "$EMAIL"

    # Expose public ports (remove override) and start nginx
    remove_override "$REMOTE" "$RPATH"
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose up -d nginx"

    # Issue TLS cert and restart nginx
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d '$DOMAIN' --email '$EMAIL' --agree-tos --no-eff-email && docker compose restart nginx"
    echo "Live at: https://$DOMAIN"
    ;;

  status)
    REMOTE=${1:-}; RPATH=${2:-$REMOTE_PATH_DEFAULT}
    [[ -z "$REMOTE" ]] && die "Usage: scripts/deploy.sh status user@host [/remote/path]"
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose ps && echo && echo 'App URL (HTTP if staging):' && (grep -E '^SERVER_NAME=' .env 2>/dev/null || true)"
    ;;

  quickstage)
    # One-shot: provision (no background builds), bind to localhost:8080, open tunnel, run core build synchronously, print ready URL
    FORCE=0; NO_TUNNEL=0
    while [[ "${1:-}" == --* ]]; do
      case "$1" in
        --force-secrets) FORCE=1 ;;
        --no-tunnel) NO_TUNNEL=1 ;;
        *) die "Unknown flag: $1" ;;
      esac; shift
    done
    REMOTE=${1:-}; RPATH=${2:-$REMOTE_PATH_DEFAULT}
    [[ -z "$REMOTE" ]] && die "Usage: scripts/deploy.sh quickstage [--force-secrets] user@host [/remote/path] [--no-tunnel]"

    ensure_remote_path "$REMOTE" "$RPATH"

    PROV_FLAGS=(--no-build --no-wiki --no-oeis)
    [[ $FORCE -eq 1 ]] && PROV_FLAGS+=(--force-secrets)
    scripts/provision_vm.sh ${PROV_FLAGS[@]} "$REMOTE" "$RPATH"

    # Local-only bind and start nginx
    write_override_localbind "$REMOTE" "$RPATH" 8080
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose up -d nginx"

    # Open tunnel unless suppressed
    if [[ $NO_TUNNEL -eq 0 ]]; then
      open_tunnel_bg "$REMOTE" 8080 8080
      READY_URL="http://localhost:8080"
    else
      echo "No tunnel requested; Nginx is bound to 127.0.0.1:8080 on the server."
      READY_URL="http://127.0.0.1:8080 (on the server via SSH)"
    fi

    echo "Running core data build (this can take a while)..."
    ssh "$REMOTE" bash -lc "cd '$RPATH' && docker compose run --rm web sage -python data_pipeline/build.py"
    echo "Core build finished. Ready at: $READY_URL"
    ;;

  *)
    cat <<USAGE
Usage:
  scripts/deploy.sh stage [--force-secrets] [--no-build] [--no-wiki] [--no-oeis] user@host [/remote/path] [--open-tunnel]
  scripts/deploy.sh live user@host example.org admin@example.org [/remote/path]
  scripts/deploy.sh status user@host [/remote/path]
  scripts/deploy.sh quickstage [--force-secrets] user@host [/remote/path] [--no-tunnel]
USAGE
    exit 1
    ;;
esac
