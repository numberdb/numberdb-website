#!/usr/bin/env bash
# Pull a database backup from the production server to this machine.
#
#     scripts/backup.sh                      # to ~/numberdb-backups
#     scripts/backup.sh /mnt/external        # somewhere else
#     REMOTE=linode scripts/backup.sh        # a different host
#
# Deliberately PULL rather than push. A push runs on the server, which means
# the server holds credentials for the backup store, and anything that can
# delete the server can delete its backups. Running from here, the server never
# has any reach into the copies, and the backups keep working when the hosting
# account itself is what went away.
#
# Run it unattended from the systemd user timer in scripts/systemd/, which
# catches up a missed run rather than skipping it -- the difference that
# matters on a laptop that is not on at three in the morning:
#
#     systemctl --user enable --now numberdb-backup.timer
#
# What this does NOT cover, on purpose:
#
#   * `.env`, which holds the secrets. It lives in Bitwarden, under the note
#     "numberdb.org production .env". Writing it here would scatter plaintext
#     credentials across every backup directory and every external drive.
#   * TLS certificates, which Let's Encrypt reissues in minutes.
#   * staticfiles and the numberdb-data checkout, both regenerated on deploy.
#
# The restore procedure is docs/runbooks/disaster-recovery.md, and it is worth
# rehearsing: an untested restore is a hypothesis, not a backup.

set -euo pipefail

REMOTE="${REMOTE:-linode}"
RPATH="${RPATH:-/opt/numberdb-website}"
DEST="${1:-$HOME/numberdb-backups}"
KEEP_DAYS="${KEEP_DAYS:-60}"

#A dump smaller than this means something went wrong: an empty database, a
#permission error swallowed by the pipe, or pg_dump writing its complaint to
#stdout. The real dump is around 14 MB compressed; 1 MB is far below anything
#plausible and far above an error message.
MIN_BYTES="${MIN_BYTES:-1000000}"

#An unattended run has no ssh agent, so the key has to be named outright.
#Without this the timer fails with "Permission denied (publickey)" while the
#same command typed by hand works -- the agent being the whole difference, and
#the least obvious one to look for.
SSH_KEY="${SSH_KEY:-}"
ssh_opts=(-o BatchMode=yes -o ClearAllForwardings=yes)
[ -n "$SSH_KEY" ] && ssh_opts+=(-o IdentitiesOnly=yes -i "$SSH_KEY")

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$DEST"
out="$DEST/numberdb-$stamp.sql.gz"

echo "[$(date -Iseconds)] backing up $REMOTE:$RPATH -> $out"

#-T because there is no terminal; without it docker allocates a TTY and
#corrupts the dump with carriage returns that psql later refuses to read.
#ClearAllForwardings: the linode host in ~/.ssh/config carries a RemoteForward
#with ExitOnForwardFailure, so a second connection aborts rather than sharing
#the port. A backup that fails because a terminal is open is a backup that
#fails on exactly the busy days.
ssh "${ssh_opts[@]}" "$REMOTE" \
	"cd $RPATH && docker compose exec -T db pg_dump -U u_numberdb --clean --if-exists numberdb" \
	| gzip -9 > "$out"

size=$(stat -c%s "$out" 2>/dev/null || stat -f%z "$out")
if [ "$size" -lt "$MIN_BYTES" ]; then
	echo "FAILED: dump is only $size bytes, expected at least $MIN_BYTES" >&2
	mv "$out" "$out.SUSPECT"
	exit 1
fi

#Checked rather than assumed. A truncated transfer produces a file that looks
#fine until the day it is needed.
if ! gzip -t "$out" 2>/dev/null; then
	echo "FAILED: $out is not valid gzip" >&2
	mv "$out" "$out.CORRUPT"
	exit 1
fi

#And that it is actually this database, not an error page or an empty schema.
#
#Decompressed once into a list rather than grepped per table: `grep -q` exits
#on its first match, which SIGPIPEs gzip, and under `set -o pipefail` that
#failure propagates and fails the check on a perfectly good dump.
present=$(gzip -dc "$out" | grep -oE '^CREATE TABLE public\.[a-z_]+' | sed 's/.*\.//' | sort -u)
for table in db_table db_number auth_user; do
	if ! printf '%s\n' "$present" | grep -qx "$table"; then
		echo "FAILED: $out contains no table $table" >&2
		mv "$out" "$out.SUSPECT"
		exit 1
	fi
done
echo "  contains $(printf '%s\n' "$present" | wc -l) tables"

echo "  ok: $(numfmt --to=iec "$size" 2>/dev/null || echo "$size bytes")"

#Retention. Old dumps are deleted only after the new one has been verified
#above, so a run that fails leaves yesterday's backup untouched.
deleted=$(find "$DEST" -maxdepth 1 -name 'numberdb-*.sql.gz' -mtime "+$KEEP_DAYS" -print -delete | wc -l)
[ "$deleted" -gt 0 ] && echo "  pruned $deleted backup(s) older than $KEEP_DAYS days"

count=$(find "$DEST" -maxdepth 1 -name 'numberdb-*.sql.gz' | wc -l)
total=$(du -sh "$DEST" 2>/dev/null | cut -f1)
echo "  $count backup(s) in $DEST, $total total"
