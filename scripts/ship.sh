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
# An unattended agent run must not be able to deploy. It may propose tables,
# fill drafts and commit; putting code on the live site is a person's act, and
# the runner sets this so that a session which talks itself into shipping is
# stopped by something other than its own judgement.
if [ "${NUMBERDB_AGENT_RUN:-0}" = "1" ]; then
	echo "Refusing: this is an agent run (NUMBERDB_AGENT_RUN=1)." >&2
	echo "Deploying is a person's act. Run it yourself when you have looked." >&2
	exit 4
fi


env_value() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"'"'"''; }

REMOTE="${1:-$(env_value DEPLOY_REMOTE)}"
RPATH="${2:-$(env_value DEPLOY_RPATH)}"
RPATH="${RPATH:-/opt/numberdb-website}"
DATA_STEPS="${DATA_STEPS:-0}"
ALLOW_DIRTY="${ALLOW_DIRTY:-0}"

[ -n "$REMOTE" ] || { echo "No remote. Set DEPLOY_REMOTE in .env or pass one." >&2; exit 2; }

say() { printf '\n=== %s\n' "$*"; }
# Every remote step is bounded, in three ways, because on 2026-09-10 the very
# first one -- putting up the banner -- hung for sixty-six minutes and took the
# site down with it. sshd on a loaded box accepts the connection and never
# completes the handshake, which looks exactly like a slow command.
#
#   * ConnectTimeout, so an unreachable host fails in seconds rather than
#     hanging on the handshake;
#   * the keepalives, so a connection that dies mid-command is noticed;
#   * `timeout`, so a remote command that never returns still ends here.
#
# The last one is the weakest: killing the local ssh does not always kill the
# remote command, which is why the compose helper below also names its
# container and removes it on the far side.
SHIP_STEP_TIMEOUT="${SHIP_STEP_TIMEOUT:-900}"
on_remote() {
	timeout "$SHIP_STEP_TIMEOUT" \
		ssh -o BatchMode=yes -o ConnectTimeout=20 \
		    -o ServerAliveInterval=15 -o ServerAliveCountMax=4 \
		    "$REMOTE" "cd '$RPATH' && $*"
}

# The same lock `agents/sage.sh` and `agents/on-server.sh` take, for the same
# reason, which this script was the last one not to take.
#
# On 2026-09-11 a deploy's `migrate` -- Sage, a few hundred megabytes -- landed
# while a campaign was running a build, beside a gunicorn worker that is Sage
# again. The box has 961 MB. The kernel killed the worker three times, swap
# filled, the load average reached 92 on one core, and the site answered
# nothing for the better part of an hour. Each of the three was within its
# budget; the sum was not.
#
# So a deploy queues behind an agent run and an agent run queues behind a
# deploy. `-w` waits rather than failing: somebody shipping wants the ship to
# happen, and a refusal would only be retyped.
LOCK="${NUMBERDB_LOCK:-/tmp/numberdb-sage.lock}"
LOCK_WAIT="${NUMBERDB_LOCK_WAIT:-3600}"

# Held per step rather than across the whole deploy, because each step is its
# own ssh session and a lock does not survive between them. The gap between
# steps is the part this cannot close: it stops the heavy work overlapping,
# which is what filled the memory.
locked() {
	on_remote "exec 9>'$LOCK'; flock -w $LOCK_WAIT 9 || { \
	           echo 'an agent run held the lock for an hour' >&2; exit 75; }; \
	           $*"
}

# Detached on the server, so killing this end cannot orphan the work.
#
# Three outages on 2026-09-11 and 2026-09-12 had one shape: a deploy step ran
# longer than the thing watching it, the local ssh was killed, and the remote
# half kept going -- unwatched, holding the lock, and pushing a 961 MB machine
# into swap until nothing answered for half an hour. `timeout` on this side
# kills the ssh and never the work, which `agents/sage.sh` has said in a
# comment since August and this script did not do.
#
# So the work is started with `setsid` behind `nohup`, writes to a file on the
# server, and this polls for the marker that says it finished. Killing this
# side now loses the *watching*, which is recoverable, rather than the
# control, which is not: the step completes, releases the lock and records its
# status, and a later ship reads it.
detached() {
	local tag="$1"; shift
	local out="/tmp/ship-$tag.out" done="/tmp/ship-$tag.done"
	on_remote "rm -f '$out' '$done'; \
		setsid nohup sh -c \"exec 9>'$LOCK'; \
			flock -w $LOCK_WAIT 9 || { echo 'lock held for an hour' >&2; echo 75 > '$done'; exit 75; }; \
			cd '$RPATH' && ( $* ); echo \\\$? > '$done'\" \
			> '$out' 2>&1 < /dev/null & echo started"

	local waited=0
	while [ "$waited" -lt "$SHIP_STEP_TIMEOUT" ]; do
		if code=$(on_remote "cat '$done' 2>/dev/null" 2>/dev/null) && [ -n "$code" ]; then
			on_remote "tail -5 '$out' 2>/dev/null" || true
			[ "$code" = "0" ] || { echo "step '$tag' failed with $code" >&2; return "$code"; }
			return 0
		fi
		sleep 10
		waited=$((waited + 10))
	done
	echo "step '$tag' is still running on the server after ${SHIP_STEP_TIMEOUT}s;" >&2
	echo "it will finish on its own -- watch $out there" >&2
	return 1
}

# A one-off container that cannot outlive the command that started it.
#
# `--no-deps` because this must never start or restart the containers serving
# the site: `docker compose run` brings dependencies up by default, and on a
# 961 MB box a second `web` beside the real one is what killed it. `--name`
# and the removal afterwards because `--rm` alone does not survive the client
# being killed -- the same belt and braces as agents/sage.sh.
compose_run() {
	local name="ship-$$-$RANDOM"
	locked "docker compose run --rm --no-deps -T --name '$name' $*; \
	        code=\$?; docker rm -f '$name' >/dev/null 2>&1; exit \$code"
}

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
notice() { compose_run "web sage -python manage.py notice $*" >/dev/null 2>&1 || true; }
notice on "\"Updating the site; it may be slow or briefly unavailable.\""

# Whatever happens next, take the banner down.
#
# It is put up here and taken down at the end, so a deploy that stops in the
# middle leaves the site telling every reader it is being updated when nothing
# is updating it. That is what happened on 2026-09-12: the migration outran
# its watcher, the ship returned early, and "Updating the site; it may be slow
# or briefly unavailable" stayed up overnight on a site that was serving
# perfectly well.
#
# A trap rather than a line at the end, because the line at the end is exactly
# what a failure skips. `notice` itself never fails, so this cannot turn a
# successful deploy into a failed one.
trap 'notice off' EXIT

# 3 ---------------------------------------------------------------------------
say "copying the code"
# The code, and not the agent runs' data. `agents/runs` holds the transcripts,
# and a campaign writes to one of them continuously: tar exits non-zero when a
# file changes while it is being read, so a deploy attempted during a campaign
# failed at this line with "file changed as we read it" and got no further.
# The server has no use for a transcript in any case -- what it needs from
# there is COSTS.tsv, which `manage.py import_agent_costs` is given
# deliberately.
tar cz --exclude='.git' --exclude='__pycache__' --exclude='staticfiles' \
       --exclude='data_pipeline/oeis-data' --exclude='.env' --exclude='.env.prod' \
       --exclude='docker-compose.override.yml' --exclude='clients/python/docs' \
       --exclude='agents/runs' --exclude='agents/critiques' \
       --exclude='agents/lessons' --exclude='agents/table-ideas/BATCH-*' \
       -C "$here" . | timeout "$SHIP_STEP_TIMEOUT" \
       	ssh -o BatchMode=yes -o ConnectTimeout=20 \
       	    -o ServerAliveInterval=15 -o ServerAliveCountMax=4 \
       	    "$REMOTE" "tar xz -C '$RPATH'"
# A tar extracts over what is there and removes nothing, so a file deleted
# from the repository stays on the server for ever. That is not academic: the
# pre-split generators for T187 and T188 were deleted here weeks ago and were
# still on the server today, still claiming those tables -- and `sage.sh` and
# the test suite read the deployed tree, so the server can run code that no
# longer exists in git.
#
# Only `generators/`, and only whole directories, and only ones the tar did
# not just write. A blanket `--delete` over $RPATH would take `.env`, the
# database volume mountpoints and everything else the repository does not
# know about.
say "removing generator directories that are no longer in git"
keep=$(printf '%s\n' generators/*/ | sed 's|generators/||;s|/$||' | sort | tr '\n' ' ')
on_remote "cd generators 2>/dev/null || exit 0; \
	for d in */; do \
		name=\${d%/}; \
		case ' $keep ' in *\" \$name \"*) ;; \
			*) echo \"  removing stale \$name\"; rm -rf \"\$name\";; \
		esac; \
	done"

# So the server can answer "what is running here" without anybody guessing.
on_remote "printf '%s\n' '$commit' > .deployed-commit"

# 4 ---------------------------------------------------------------------------
say "building"
detached build-web "docker compose build web"
# nginx carries configuration from this repo -- the anonymised log format, the
# TLS templates -- so a deploy that only ever built `web` shipped those changes
# to the server's disk and then ran the old image, forever. Cheap: unchanged
# inputs mean a cached build and no recreate below.
detached build-nginx "docker compose build nginx"
say "migrating"
detached migrate "docker compose run --rm --no-deps -T --name ship-migrate-$$ web sage -python manage.py migrate; code=\$?; docker rm -f ship-migrate-$$ >/dev/null 2>&1; exit \$code"

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
#Under the lock as well: recreating web starts a fresh Sage import, and
#doing that beside an agent run is half of what filled the memory.
detached restart "docker compose up -d web nginx"
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
