#!/usr/bin/env bash
# Deploy the current commit to a running numberdb host. One command, repeatable.
#
#     scripts/ship.sh                     # to $DEPLOY_REMOTE from .env
#     scripts/ship.sh root@host /opt/numberdb-website
#     DATA_STEPS=1 scripts/ship.sh        # also run the one-off importers
#
# This exists because deploying was done by hand, and by hand it went like
# this: `make deploy_live` turned out not to ship code or run migrations at all
# -- it sets env keys, exposes ports and renews TLS -- while `deploy_stage`
# rewrites the compose override and can take the public site dark. The steps
# that actually work were discovered one at a time, in the wrong order, on a
# live site. They are written down here instead.
#
# What it does, in the order that matters:
#
#   1. refuses to ship a dirty tree, so what runs in production exists in git
#   2. puts up the maintenance banner
#   3. copies the code, never .env -- production keeps its own secrets
#   4. builds the image and runs migrations
#   5. restarts web, because `docker compose run` uses the new image while the
#      container serving pages keeps the old one until it is recreated
#   6. smoke-tests real pages and rolls the banner down only if they answer
#
# What it deliberately does NOT do: touch nginx, TLS, ports, or the database's
# contents. Those are provisioning and one-off migrations, and mixing them into
# the everyday path is how an ordinary deploy takes a site down.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

env_value() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"''; }

REMOTE="${1:-$(env_value DEPLOY_REMOTE)}"
RPATH="${2:-$(env_value DEPLOY_RPATH)}"
RPATH="${RPATH:-/opt/numberdb-website}"
DATA_STEPS="${DATA_STEPS:-0}"
ALLOW_DIRTY="${ALLOW_DIRTY:-0}"

[ -n "$REMOTE" ] || { echo "No remote. Set DEPLOY_REMOTE in .env or pass one." >&2; exit 2; }

say() { printf '\n=== %s\n' "$*"; }
on_remote() { ssh -o BatchMode=yes "$REMOTE" "cd '$RPATH' && $*"; }

# 1 ---------------------------------------------------------------------------
# Production ran four uncommitted files for a while because the copy takes the
# working tree, not the commit. Anything not in git cannot be rolled back to,
# reviewed, or found again after the laptop it lived on is gone.
dirty=$(git status --porcelain --untracked-files=no | wc -l)
if [ "$dirty" -gt 0 ] && [ "$ALLOW_DIRTY" != "1" ]; then
	echo "Refusing: $dirty tracked file(s) modified but not committed." >&2
	git status --short --untracked-files=no >&2
	echo "Commit them, or ALLOW_DIRTY=1 if you really mean to ship them." >&2
	exit 3
fi
commit=$(git rev-parse HEAD)
say "shipping $(git rev-parse --short HEAD) to $REMOTE:$RPATH"

# 2 ---------------------------------------------------------------------------
notice() { on_remote "docker compose run --rm -T web sage -python manage.py notice $*" >/dev/null 2>&1 || true; }
notice on "\"Updating the site; it may be slow or briefly unavailable.\""

# 3 ---------------------------------------------------------------------------
say "copying the code"
tar cz --exclude='.git' --exclude='__pycache__' --exclude='staticfiles' \
       --exclude='data_pipeline/oeis-data' --exclude='.env' --exclude='.env.prod' \
       --exclude='docker-compose.override.yml' --exclude='clients/python/docs' \
       -C "$here" . | ssh -o BatchMode=yes "$REMOTE" "tar xz -C '$RPATH'"
# So the server can answer "what is running here" without anybody guessing.
on_remote "printf '%s\n' '$commit' > .deployed-commit"

# 4 ---------------------------------------------------------------------------
say "building"
on_remote "docker compose build web" | tail -2
# nginx carries configuration from this repo -- the anonymised log format, the
# TLS templates -- so a deploy that only ever built `web` shipped those changes
# to the server's disk and then ran the old image, forever. Cheap: unchanged
# inputs mean a cached build and no recreate below.
on_remote "docker compose build nginx" | tail -2
say "migrating"
on_remote "docker compose run --rm -T web sage -python manage.py migrate" | tail -8

# 5 ---------------------------------------------------------------------------
if [ "$DATA_STEPS" = "1" ]; then
	say "one-off data steps (detached: these rebuild every table and outlast an ssh timeout)"
	for step in import_table_history import_table_files flatten_tables hoist_param_labels; do
		echo "  $step"
		on_remote "nohup docker compose run --rm -T web sage -python manage.py $step > /tmp/$step.log 2>&1"
		on_remote "tail -1 /tmp/$step.log"
	done
fi

say "restarting web and nginx"
# Compose recreates only what actually changed, so naming both here costs
# nothing when nginx is untouched. Other services (db, evaluator) pick up
# compose-file changes -- log rotation, limits -- the next time they are
# recreated, which is deliberately not on every deploy.
on_remote "docker compose up -d web nginx" | tail -3
sleep 15

# 6 ---------------------------------------------------------------------------
say "checking it answers"
domain=$(on_remote "grep -E '^SERVER_NAME=' .env | cut -d= -f2-" | tr -d '"'"'"'' | tr -d '\r')
domain="${domain:-numberdb.org}"
failed=0
for path in / /help /api/docs /tables; do
	code=$(on_remote "curl -s -o /dev/null -m 25 -w '%{http_code}' -k --resolve $domain:443:127.0.0.1 https://$domain$path")
	printf '  %-12s %s\n' "$path" "$code"
	[ "$code" = "200" ] || failed=1
done

# A page that answers 200 can still be answering nothing. This asks the one
# question the site exists to answer -- here is a number, is it known? -- and
# insists on the table by name. Searching for pi stopped finding the table
# called Pi for three days in August 2026, because a metadata edit had marked
# the whole corpus unreviewed and unreviewed values are held out of search by
# number. Every page returned 200 throughout.
say "checking search by number still answers"
for probe in "3.14159265:Pi" "1.6180339887:Golden_ratio"; do
	query="${probe%%:*}"
	expected="${probe##*:}"
	found=$(on_remote "curl -s -m 25 -k --resolve $domain:443:127.0.0.1 -H 'X-Requested-With: XMLHttpRequest' 'https://$domain/?q=$query'" | grep -c "$expected" || true)
	if [ "${found:-0}" -gt 0 ]; then
		printf '  %-14s finds %s\n' "$query" "$expected"
	else
		printf '  %-14s DOES NOT FIND %s\n' "$query" "$expected"
		failed=1
	fi
done

if [ "$failed" = "1" ]; then
	cat >&2 <<'MSG'

The site is not answering. The banner has been left up on purpose.

  logs:      ssh REMOTE 'cd RPATH && docker compose logs --tail 60 web'
  roll back: check out the previous commit and run this script again; the
             database is forward-migrated, so also restore a backup if the
             migrations are what broke it.
MSG
	exit 1
fi

notice off
say "done: $(git rev-parse --short HEAD) is live at https://$domain"
