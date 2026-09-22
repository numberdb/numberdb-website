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
LOCAL=no
case "$REMOTE" in local|localhost) LOCAL=yes ;; esac

if [ "$LOCAL" = yes ] && [ -z "${NUMBERDB_RPATH:-}" ]; then
	RPATH="$here"
else
	RPATH="${NUMBERDB_RPATH:-/opt/numberdb-website}"
fi
TIMEOUT="${NUMBERDB_TIMEOUT:-1800}"
LOCK="/tmp/numberdb-sage.lock"

[ $# -ge 1 ] || { echo "usage: $0 <command...>" >&2; exit 2; }

name="numberdb-on-server-$$"
ssh_opts=(-o BatchMode=yes -o ExitOnForwardFailure=no
          -o ControlMaster=auto -o ControlPath=/tmp/numberdb-ssh-%r@%h:%p
          -o ControlPersist=60)

# The whole test suite does not fit on the machine that serves the site.
#
# The lock above serialises runs against each other. It says nothing about
# what one run weighs, and the suite is the heaviest thing anybody points at
# this script: it builds a test database beside the live one and loads Django
# and Sage to do it. On 2026-09-22 that ran against a 961 MB box already
# holding web, nginx, evaluator, Postgres and three unrelated containers, and
# the kernel ended it:
#
#     systemd invoked oom-killer: ... global_oom
#     Out of memory: Killed process 1021001 (python3) total-vm:1935744kB
#
# numberdb.org was unreachable for about twenty minutes -- not crashed, but
# starved: every port still accepted TCP and nothing could answer, sshd
# included, so the box could not even be looked at. It recovered on its own
# when the suite died.
#
# A *targeted* run is fine and is what this is for: 125 tests named by module
# passed on the same box minutes earlier. What is refused is the unbounded
# form -- `manage.py test`, or a bare app label -- on a host too small to
# hold it. Named by the host's memory rather than by what is free at the
# moment, because a guard that depends on load passes exactly when the
# machine is quiet and the temptation is greatest.
names_a_module() {
	#`numberdb_app.test_runner` is targeted; `numberdb_app` is not.
	#
	#Only the words *after* `test`, and never a `.py` path: the first version
	#matched any dotted argument anywhere, so `manage.py` -- which is in every
	#invocation there is -- read as a named module and waved the whole suite
	#through. It was written, tested once against a command that happened to
	#be targeted, and then let the untargeted form run on the live server
	#while its author watched the trace.
	local seen=no arg
	for arg in "$@"; do
		if [ "$seen" = yes ]; then
			case "$arg" in
				-*)   ;;                 #a flag, not a target
				*.py) ;;                 #a script path, not a module
				*.*)  return 0 ;;        #dotted: a module path
			esac
		fi
		[ "$arg" = test ] && seen=yes
	done
	return 1
}

if printf '%s\n' "$@" | grep -qx 'test' && ! names_a_module "$@" \
		&& [ "${NUMBERDB_ALLOW_BIG_TEST:-0}" != "1" ]; then
	read_total_mb="free -m 2>/dev/null | awk '/^Mem:/{print \$2}'"
	if [ "$LOCAL" = yes ]; then
		total_mb=$(bash -c "$read_total_mb" 2>/dev/null || echo '')
	else
		total_mb=$(ssh -n "${ssh_opts[@]}" "$REMOTE" "$read_total_mb" \
		           2>/dev/null || echo '')
	fi
	floor="${NUMBERDB_TEST_MIN_MB:-2000}"
	#Fail closed. A guard that waves the run through when it cannot read the
	#machine is not a guard: it would have passed on exactly the afternoon
	#this was written for, when the box was too busy to answer anything.
	if [ -z "$total_mb" ] || ! [ "$total_mb" -ge 0 ] 2>/dev/null; then
		echo "Refusing: could not read how much memory the target has, and" >&2
		echo "the whole suite is the one command that must not be guessed at." >&2
		echo "Name a module to test, or NUMBERDB_ALLOW_BIG_TEST=1 to insist." >&2
		exit 4
	fi
	if [ "$total_mb" -lt "$floor" ] 2>/dev/null; then
		echo "Refusing: the whole test suite on a ${total_mb} MB machine." >&2
		echo "It needs more than that beside the site, and the site is what" >&2
		echo "starves: on 2026-09-22 this took numberdb.org down for twenty" >&2
		echo "minutes and the box could not be reached to see why." >&2
		echo >&2
		echo "Name what you want to test instead -- that is what runs here:" >&2
		echo "    $0 manage.py test numberdb_app.test_runner --noinput" >&2
		echo >&2
		echo "NUMBERDB_ALLOW_BIG_TEST=1 to insist anyway." >&2
		exit 4
	fi
fi

mounted=""
#`generators` among them because test_skill asserts things about those
#files -- that each says how to install the package it imports, and says
#it near the top. Unmounted, the suite read the image's copy and a fix in
#the working tree could not be tested until it had been shipped.
for dir in numberdb_app data_pipeline agents docs utils scripts numberdb clients generators .claude; do
	mounted="$mounted -v $RPATH/$dir:/app/$dir:ro"
done

cleanup() {
	#The container as well: a timeout on this side kills the ssh and leaves
	#the work running, which is how a suite came to be racing a test run.
	if [ "$LOCAL" = yes ]; then
		docker rm -f "$name" >/dev/null 2>&1 || true
	else
		ssh -n "${ssh_opts[@]}" "$REMOTE" "docker rm -f '$name' >/dev/null 2>&1" \
			>/dev/null 2>&1 || true
	fi
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

command="exec 9>'$LOCK'; flock -w 3600 9 || { echo 'another run held the lock for an hour' >&2; exit 75; }; \
 cd '$RPATH' && timeout $TIMEOUT docker compose run --rm --no-deps -T --name '$name' \
 $env_args $mounted web sage -python $remote_args; code=\$?; docker rm -f '$name' >/dev/null 2>&1; exit \$code"

if [ "$LOCAL" = yes ]; then
	bash -c "$command"
else
	ssh "${ssh_opts[@]}" "$REMOTE" "$command"
fi
