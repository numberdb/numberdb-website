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

main=$1
[ -f "$main" ] || { echo "no such file: $main" >&2; exit 2; }

# A colliding remote forward makes ssh exit 255 having printed nothing, which
# reads exactly like a dead server. Tolerate it.
ssh_opts=(-o BatchMode=yes -o ExitOnForwardFailure=no)

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
ssh "${ssh_opts[@]}" "$REMOTE" "chmod 644 $remote_dir.* 2>/dev/null || true"

cleanup() {
	ssh "${ssh_opts[@]}" "$REMOTE" "rm -f $remote_dir.*" >/dev/null 2>&1 || true
}
trap cleanup EXIT

ssh "${ssh_opts[@]}" "$REMOTE" "mkdir -p /dev/null" >/dev/null 2>&1 || true

# --no-deps so this never restarts the site's own containers.
ssh "${ssh_opts[@]}" "$REMOTE" \
	"cd '$RPATH' && timeout $TIMEOUT docker compose run --rm --no-deps -T \
		-e PYTHONPATH=/app/clients/python \
		-e NUMBERDB_ASSISTED_BY='${NUMBERDB_ASSISTED_BY:-assisted by an agent}' \
		${mounts[*]} \
		web sage -python /work/$(basename "$main")" \
	2>&1 | grep -viE 'collecting static|static files copied|Starting command as|^ Container |remote port forwarding'
