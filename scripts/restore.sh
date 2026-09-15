#!/usr/bin/env bash
# Put a backup back, or prove that one would go back.
#
#     scripts/restore.sh --verify                       # newest backup, into a scratch database
#     scripts/restore.sh --verify numberdb-2026....gz   # a particular one
#     scripts/restore.sh --to root@newhost              # a fresh machine, for real
#
# `--verify` is the one to run often, and it is safe: it restores into a
# throwaway database beside the real one, counts what came back, and drops it.
# It touches nothing that is being used. An untested restore is a hypothesis,
# and the day you find out is the day it has to work.
#
# `--to` is the disaster. It expects a host where the stack is already up --
# docs/runbooks/disaster-recovery.md gets you that far, since it needs the
# secrets out of Bitwarden and DNS pointed at the new address, neither of which
# a script should be doing on its own.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

DEST="${BACKUPS:-$HOME/numberdb-backups}"
LOCAL_COMPOSE="${LOCAL_COMPOSE:-docker compose}"
RPATH="${RPATH:-/opt/numberdb-website}"

mode=""; target=""; dump=""
while [ $# -gt 0 ]; do
	case "$1" in
		--verify) mode=verify ;;
		--to) mode=to; target="${2:-}"; shift ;;
		-*) echo "Unknown flag: $1" >&2; exit 2 ;;
		*) dump="$1" ;;
	esac
	shift
done
[ -n "$mode" ] || { sed -n '2,12p' "$0"; exit 2; }

# Where the dump comes from: a `.sql.gz` if one was named or one is lying
# there, otherwise the newest restic snapshot. `read_dump` is the only place
# that knows which, so the two restores below are the same code either way.
#
# A snapshot rather than a file is the normal case now -- see the note in
# scripts/backup.sh about sixty copies of one day -- and the `.sql.gz` path
# stays because backups taken before the change are still backups.
#The same choice backup.sh makes, for the same reason: the distribution's
#restic may be too old to read a repository this one wrote.
RESTIC="${NUMBERDB_RESTIC:-}"
if [ -z "$RESTIC" ]; then
	if [ -x "$HOME/.local/bin/restic" ]; then
		RESTIC="$HOME/.local/bin/restic"
	else
		RESTIC=restic
	fi
fi

RESTIC_REPO="${NUMBERDB_RESTIC_REPO:-$DEST/repo}"
RESTIC_PASSWORD_FILE="${NUMBERDB_RESTIC_PASSWORD_FILE:-$HOME/.config/numberdb/restic-password}"
snapshot=""

if [ -z "$dump" ]; then
	dump=$(ls -1t "$DEST"/numberdb-*.sql.gz 2>/dev/null | head -1 || true)
	if [ -z "$dump" ] && command -v "$RESTIC" >/dev/null 2>&1 	   && [ -s "$RESTIC_PASSWORD_FILE" ]; then
		export RESTIC_PASSWORD_FILE RESTIC_REPOSITORY="$RESTIC_REPO"
		snapshot="${NUMBERDB_SNAPSHOT:-latest}"
	fi
fi

if [ -n "$snapshot" ]; then
	#Ask the snapshot where the file is rather than assuming: restic
	#records the absolute path it backed up, and a repository opened on a
	#machine whose home directory is not this one would otherwise not be
	#readable by its own restore script.
	inside=$("$RESTIC" snapshots "$snapshot" --json \
		| python3 -c 'import json,sys; print(json.load(sys.stdin)[-1]["paths"][0])')
	echo "using restic snapshot $snapshot from $RESTIC_REPO ($inside)"
	read_dump() { "$RESTIC" dump "$snapshot" "$inside"; }
else
	[ -n "$dump" ] && [ -f "$dump" ] || { echo "No backup found in $DEST" >&2; exit 2; }
	echo "using $dump ($(du -h "$dump" | cut -f1))"
	read_dump() { gzip -dc "$dump"; }
fi

# What a restored database has to contain to count as restored. Read back
# rather than trusting psql's exit code: a dump can apply cleanly and still be
# empty.
#
# Counted only where the table exists, because a backup older than a migration
# is still a backup -- the first rehearsal of this script was against a dump
# taken twenty minutes before the revisions table did, and a query that simply
# failed there would have said "your backup is broken" about a good backup.
counts_sql="
do \$\$
declare
  t text;
  n bigint;
begin
  create temporary table restored(what text, rows bigint) on commit drop;
  foreach t in array array['db_table','db_number','db_tablerevision',
                           'db_attachment','db_blob','db_tag','auth_user'] loop
    if to_regclass('public.' || t) is null then
      insert into restored values (t, null);
    else
      execute format('select count(*) from %I', t) into n;
      insert into restored values (t, n);
    end if;
  end loop;
  create temporary table shown as select * from restored;
end
\$\$;
select what as \"table\",
       coalesce(rows::text, 'not in this dump') as rows
from shown order by what;"

case "$mode" in

verify)
	# Beside the real database, never into it. The name says what it is, in
	# case anybody finds it later.
	scratch="numberdb_restore_check"
	echo "restoring into $scratch on the local stack"
	$LOCAL_COMPOSE exec -T db psql -U u_numberdb -d postgres \
		-c "drop database if exists $scratch;" -c "create database $scratch;" >/dev/null
	read_dump | $LOCAL_COMPOSE exec -T db psql -q -U u_numberdb -d "$scratch" \
		-v ON_ERROR_STOP=0 >/dev/null 2>&1 || true
	echo
	$LOCAL_COMPOSE exec -T db psql -U u_numberdb -d "$scratch" -c "$counts_sql"
	$LOCAL_COMPOSE exec -T db psql -U u_numberdb -d postgres \
		-c "drop database $scratch;" >/dev/null
	echo "scratch database dropped."
	echo
	echo "If those counts look like the site, the backup is a backup."
	;;

to)
	[ -n "$target" ] || { echo "--to needs user@host" >&2; exit 2; }
	echo
	echo "About to REPLACE the database on $target."
	echo "Everything now in it is dropped and the dump put in its place."
	printf 'Type the host name to continue: '
	read -r confirm
	[ "$confirm" = "${target#*@}" ] || { echo "Not confirmed."; exit 1; }

	echo "stopping the app so nothing writes while the tables are replaced"
	ssh -o BatchMode=yes "$target" "cd '$RPATH' && docker compose stop web" >/dev/null
	read_dump | ssh -o BatchMode=yes "$target" \
		"cd '$RPATH' && docker compose exec -T db psql -q -U u_numberdb -d numberdb"
	echo "starting the app"
	ssh -o BatchMode=yes "$target" "cd '$RPATH' && docker compose up -d web" >/dev/null
	sleep 15
	ssh -o BatchMode=yes "$target" \
		"cd '$RPATH' && docker compose exec -T db psql -U u_numberdb -d numberdb -c \"$counts_sql\""
	;;
esac
