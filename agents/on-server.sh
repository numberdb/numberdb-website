#!/usr/bin/env bash
# Run one command in a throwaway container on the server, under the lock.
#
#     agents/on-server.sh manage.py test numberdb_app --noinput
#     agents/on-server.sh manage.py audit_table T133
#
# This exists because `agents/sage.sh` holds a lock and everything else did
# not. The lock stopped two agent runs colliding; it never stopped *me*
# starting a test suite beside one, which is what took the server down three
# times in a day. The rule was "one thing at a time on that server", and a
# rule that has to be remembered at the moment of temptation is not a control.
#
# The same lock as sage.sh, so an agent run and a test suite queue behind each
# other rather than competing.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

REMOTE="${NUMBERDB_REMOTE:-linode}"
RPATH="${NUMBERDB_RPATH:-/opt/numberdb-website}"
TIMEOUT="${NUMBERDB_TIMEOUT:-1800}"
LOCK="/tmp/numberdb-sage.lock"

[ $# -ge 1 ] || { echo "usage: $0 <command...>" >&2; exit 2; }

name="numberdb-on-server-$$"
ssh_opts=(-o BatchMode=yes -o ExitOnForwardFailure=no
          -o ControlMaster=auto -o ControlPath=/tmp/numberdb-ssh-%r@%h:%p
          -o ControlPersist=60)

mounted=""
for dir in numberdb_app data_pipeline agents docs utils scripts numberdb clients .claude; do
	mounted="$mounted -v $RPATH/$dir:/app/$dir:ro"
done

cleanup() {
	#The container as well: a timeout on this side kills the ssh and leaves
	#the work running, which is how a suite came to be racing a test run.
	ssh -n "${ssh_opts[@]}" "$REMOTE" "docker rm -f '$name' >/dev/null 2>&1" \
		>/dev/null 2>&1 || true
}
trap cleanup EXIT

# The command crosses an ssh boundary and is parsed once more by the remote
# shell, so every argument is quoted for it. Unquoted, an argument containing
# brackets or a redirect was torn apart there:
#
#     manage.py shell -c "exec(open('x.py').read())"
#     -> bash: syntax error near unexpected token `('
#
# NUMBERDB_ENV passes variables into the container, space-separated NAME=value
# pairs, because `docker compose run` does not inherit this shell's.
remote_args=$(printf '%q ' "$@")
env_args=''
for pair in ${NUMBERDB_ENV:-}; do
	env_args="$env_args -e $(printf '%q' "$pair")"
done

ssh "${ssh_opts[@]}" "$REMOTE" \
	"exec 9>'$LOCK'; flock -w 3600 9 || { echo 'another run held the lock for an hour' >&2; exit 75; }; \
	 cd '$RPATH' && timeout $TIMEOUT docker compose run --rm --no-deps -T --name '$name' \
	 $env_args $mounted web sage -python $remote_args; code=\$?; docker rm -f '$name' >/dev/null 2>&1; exit \$code"
