#!/usr/bin/env bash
# Run a Python file under SageMath, against numberdb, without touching the site.
#
#     agents/sage.sh path/to/script.py [more files to mount...]
#
# The script runs in a throwaway container built from the deployed image, with
# the repository's client package on the path and the file mounted read-only.
# It is the only way an agent should run Sage here, and it exists because the
# alternatives have all gone wrong:
#
#   * `docker compose exec web ...` runs inside the container serving the site.
#     On 2026-08-30 that took every table page down for several minutes, because
#     files copied in for a test referred to a database column whose migration
#     had not been applied. A test must not be able to do that.
#   * `sage -python script.py` puts the script's own directory on sys.path and
#     not the working directory, so `import numberdb` finds the Django project
#     package -- which has no client API -- or nothing at all.
#   * the client is not installed in the image. It lives in the repository at
#     clients/python and has to be put on PYTHONPATH.
#
# The key, if the script needs one, arrives on stdin and never as an argument:
#
#     cat ~/.config/numberdb/zeta3-key | agents/sage.sh fill.py
#
# Nothing here can publish a table. That is enforced on the server by the
# account the key belongs to, not by this script.

set -euo pipefail

REMOTE="${NUMBERDB_REMOTE:-linode}"
RPATH="${NUMBERDB_RPATH:-/opt/numberdb-website}"
TIMEOUT="${NUMBERDB_TIMEOUT:-1800}"

[ $# -ge 1 ] || { echo "usage: $0 script.py [more.py ...]" >&2; exit 2; }

# One run at a time, enforced rather than remembered.
#
# This server has 961 MB. Two Sage processes on it drive the load average past
# 70, and sshd then accepts TCP connections without ever completing a
# handshake -- which is indistinguishable from the machine being down, and
# takes tens of minutes to clear. It has happened twice, both times because a
# second run was started while the first was still going, and both times the
# rule against it existed and was simply not followed.
#
# `flock` makes it impossible instead. The lock is held on the server for the
# life of the command, so it applies across sessions and across people, not
# just within one script.
LOCK="/tmp/numberdb-sage.lock"


main=$1
[ -f "$main" ] || { echo "no such file: $main" >&2; exit 2; }

# A colliding remote forward makes ssh exit 255 having printed nothing, which
# reads exactly like a dead server. Tolerate it.
# One connection per run, not three. Each call here opened a new ssh for the
# copy, another for the chmod, another for the command, and a run makes many
# calls; enough of them at once and sshd stops completing handshakes, which
# looks exactly like the server being down. Multiplexing puts them all through
# the first connection, which is also faster.
control="/tmp/numberdb-ssh-%r@%h:%p"
ssh_opts=(-o BatchMode=yes -o ExitOnForwardFailure=no
          -o ControlMaster=auto -o "ControlPath=$control" -o ControlPersist=60)

remote_dir="/tmp/agent-run-$$"
mounts=()
for file in "$@"; do
	[ -f "$file" ] || { echo "no such file: $file" >&2; exit 2; }
	base=$(basename "$file")
	scp -q "${ssh_opts[@]}" "$file" "$REMOTE:$remote_dir.$base"
	mounts+=(-v "$remote_dir.$base:/work/$base:ro")
done

# The container runs as a different user from the one that owns these copies,
# so a file that arrived mode 600 -- anything from `mktemp`, for instance -- is
# unreadable inside it, and the error names the file rather than the cause.
# Make them readable once, here, rather than expecting every caller to know.
#
# `-n` on every ssh call but the last: ssh forwards its stdin to the remote
# command, so without it the first helper call here swallowed the API key that
# was piped in for the script, and the script was told it had no key.
ssh -n "${ssh_opts[@]}" "$REMOTE" "chmod 644 $remote_dir.* 2>/dev/null || true"

cleanup() {
	#The container as well as the copies. A `timeout` on this side kills the
	#local ssh and leaves the remote work running, and an abandoned Sage
	#process is what takes the machine down.
	ssh -n "${ssh_opts[@]}" "$REMOTE" \
		"rm -f $remote_dir.*; docker rm -f 'numberdb-agent-run-$$' >/dev/null 2>&1" \
		>/dev/null 2>&1 || true
}
trap cleanup EXIT

# --no-deps so this never restarts the site's own containers.
# `flock -w` waits rather than failing outright: a queued run is what somebody
# wants, and a refusal would only be retried by hand. `--rm` and a name let the
# cleanup below reach the container if this end dies first, which is the other
# half of the problem -- `timeout` here kills the ssh, never the work.
name="numberdb-agent-run-$$"
ssh "${ssh_opts[@]}" "$REMOTE" \
	"exec 9>'$LOCK'; flock -w 3600 9 || { echo 'another run held the lock for an hour' >&2; exit 75; }; \
	 cd '$RPATH' && timeout $TIMEOUT docker compose run --rm --no-deps -T --name '$name' \
		-e PYTHONPATH=/app/clients/python \
		-e NUMBERDB_ASSISTED_BY='${NUMBERDB_ASSISTED_BY:-assisted by an agent}' \
		${mounts[*]} \
		web sage -python /work/$(basename "$main")" \
	2>&1 | grep -viE 'collecting static|static files copied|Starting command as|^ Container |remote port forwarding'
