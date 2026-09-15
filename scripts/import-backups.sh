#!/usr/bin/env bash
# Put the old `numberdb-<stamp>.sql.gz` dumps into the restic repository.
#
#     scripts/import-backups.sh              # import, keep the .gz files
#     scripts/import-backups.sh --delete     # import, then remove each one
#
# A one-off, for the changeover. The history in those files is worth keeping
# and costs almost nothing once it is stored as chunks: they are ninety-odd
# per cent the same bytes as each other.
#
# Each snapshot is dated from the dump's own stamp rather than from now, so
# `restic snapshots` shows the nights the backups were actually taken and
# `forget --keep-daily/weekly/monthly` thins them by the same policy as the
# ones taken since.
#
# Oldest first, so that the repository grows the way it would have if these
# had been taken this way all along -- and so that an interrupted run leaves a
# prefix of the history rather than a hole in the middle.
set -euo pipefail

delete=no
if [ "${1:-}" = "--delete" ]; then
	delete=yes
	shift
fi
DEST="${1:-$HOME/numberdb-backups}"

RESTIC="${NUMBERDB_RESTIC:-}"
if [ -z "$RESTIC" ]; then
	if [ -x "$HOME/.local/bin/restic" ]; then
		RESTIC="$HOME/.local/bin/restic"
	else
		RESTIC=restic
	fi
fi
export RESTIC_REPOSITORY="${NUMBERDB_RESTIC_REPO:-$DEST/repo}"
export RESTIC_PASSWORD_FILE="${NUMBERDB_RESTIC_PASSWORD_FILE:-$HOME/.config/numberdb/restic-password}"
export RESTIC_COMPRESSION="${RESTIC_COMPRESSION:-max}"

[ -s "$RESTIC_PASSWORD_FILE" ] || { echo "no repository password at $RESTIC_PASSWORD_FILE" >&2; exit 2; }
"$RESTIC" cat config >/dev/null 2>&1 || { echo "no repository at $RESTIC_REPOSITORY; run scripts/backup.sh once" >&2; exit 2; }

#The same staging path backup.sh uses, so that every snapshot in the
#repository names the same file and a restore does not have to care which run
#made it.
staging="$DEST/.staging"
plain="$staging/numberdb.sql"
rm -rf "$staging"
mkdir -p "$staging"
trap 'rm -rf "$staging"' EXIT

before=$(du -sm "$RESTIC_REPOSITORY" | cut -f1)
imported=0

for dump in $(ls -1 "$DEST"/numberdb-*.sql.gz 2>/dev/null | sort); do
	name=$(basename "$dump")
	stamp=${name#numberdb-}
	stamp=${stamp%.sql.gz}
	when="${stamp:0:4}-${stamp:4:2}-${stamp:6:2} ${stamp:9:2}:${stamp:11:2}:${stamp:13:2}"

	#A file too small to be a dump is not one. Two of the first fifty-one here
	#were 20 and 980 bytes, and importing those would put a snapshot in the
	#repository that restores to nothing.
	size=$(stat -c%s "$dump")
	if [ "$size" -lt "${MIN_BYTES:-1000000}" ]; then
		echo "  $name is $size bytes; not a dump, skipping"
		continue
	fi

	gzip -dc "$dump" > "$plain"
	if ! tail -c 200 "$plain" | grep -q 'PostgreSQL database dump complete'; then
		echo "  $name does not end with pg_dump's completion line; skipping"
		continue
	fi

	"$RESTIC" backup --quiet --host numberdb --tag database --tag imported \
		--time "$when" "$plain"
	imported=$((imported + 1))
	echo "  $name -> snapshot dated $when"
	[ "$delete" = yes ] && rm -f "$dump"
done

after=$(du -sm "$RESTIC_REPOSITORY" | cut -f1)
echo
echo "imported $imported dump(s); the repository went from ${before} MB to ${after} MB"
"$RESTIC" snapshots --host numberdb --compact 2>/dev/null | tail -5
[ "$delete" = no ] && echo "
The .gz files are still there. Once you have restored one snapshot to your own
satisfaction -- scripts/restore.sh --verify, or restic dump -- they are
redundant: rerun with --delete, or use scripts/thin-backups.sh."
