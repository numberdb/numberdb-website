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
#     cat ~/.config/numberdb/zeta3-key | NUMBERDB_KEY_FROM_STDIN=1 \
#         agents/sage.sh fill.py
#
# NUMBERDB_KEY_FROM_STDIN and NUMBERDB_PUBLISH are forwarded into the
# container, because a generator's `__main__` reads both and this script
# passes no arguments, so `--publish` cannot be given. Without the first the
# script never reads the pipe and goes to the API with no key: a read of a
# *draft* then answers "does not exist", which reads like the table was never
# created rather than like a missing credential. Filling T169 and verifying
# T172 each lost a run to that.
#
# NUMBERDB_PUBLISH sends a generator's *numbers* to a table its key may
# already write. It does not make a table public: that is `publish_table`,
# which is on the site, behind review, and reachable from nothing here.
#
# Nothing here can publish a table. That is enforced on the server by the
# account the key belongs to, not by this script.

set -euo pipefail

REMOTE="${NUMBERDB_REMOTE:-linode}"

# Running on the machine that has the image, rather than reaching one.
#
# When the agents run on the build box themselves -- which is the point of
# having one, so a campaign does not stop because a laptop slept -- the Sage
# host is this host, and ssh'ing to yourself to run a container is a knot for
# no gain. `NUMBERDB_REMOTE=local` skips ssh and scp entirely.
#
# Everything else is identical: the same lock, the same timeout, the same
# memory cap, the same image. A run should not be able to tell.
LOCAL=no
case "$REMOTE" in local|localhost) LOCAL=yes ;; esac

# One pair of helpers so the call sites below read the same either way.
run_there() {
	if [ "$LOCAL" = yes ]; then
		bash -c "$*"
	else
		ssh "${ssh_opts[@]}" "$REMOTE" "$*"
	fi
}

run_there_quietly() {
	if [ "$LOCAL" = yes ]; then
		bash -c "$*" </dev/null
	else
		ssh -n "${ssh_opts[@]}" "$REMOTE" "$*"
	fi
}

put_there() {
	if [ "$LOCAL" = yes ]; then
		cp "$1" "$2"
	else
		scp -q "${ssh_opts[@]}" "$1" "$REMOTE:$2" </dev/null
	fi
}
RPATH="${NUMBERDB_RPATH:-/opt/numberdb-website}"
TIMEOUT="${NUMBERDB_TIMEOUT:-1800}"

# Which image a run happens in, and how much of the machine it may take.
#
# The website's image is the default because for a long time it was the only
# one: the sole machine with Sage was the one serving pages, so a build ran in
# the image that serves pages. That is also how a build-time dependency
# becomes a production one -- two tables want SnapPy, and the choice was
# either to put a knot-theory library on the web server or leave the tables as
# stubs.
#
#     NUMBERDB_REMOTE=builder NUMBERDB_SAGE_IMAGE=numberdb/builder:latest
#
# points a run at a machine that does nothing else, running an image with no
# Django and no app, which talks to numberdb.org over the public API like any
# outside contributor. Nothing else about this script changes, because nothing
# else about a run depends on where it happens.
IMAGE="${NUMBERDB_SAGE_IMAGE:-numberdb/web:latest}"
MEMORY="${NUMBERDB_SAGE_MEMORY:-320m}"
# Where the client lives in that image. In the website's it is the repository
# copy at /app; the builder installs it and sets its own, so this is passed
# only when it is set to something.
CLIENT_PATH="${NUMBERDB_SAGE_PYTHONPATH-/app/clients/python}"
pythonpath=()
[ -n "$CLIENT_PATH" ] && pythonpath=(-e "PYTHONPATH=$CLIENT_PATH")

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
# One slot, or one slot per worker.
#
# The paragraph above is about a 961 MB machine with two cores, where one Sage
# process is all there is room for. That is still the default, and a laptop or
# a one-off `agents/sage.sh` gets it without asking.
#
# It is the wrong bound for a machine bought to hold more. On 2026-09-22 four
# builders drew Sage-heavy proposals from one family and serialised behind
# this single lock: three of them sat 2h26m with 18 to 32 seconds of CPU
# between them, and one gave up mid-build and left an empty draft. The
# contention was not a bug in any of them; it was four workers sharing one
# slot.
#
# So the slot is named. `NUMBERDB_SAGE_SLOT=w3` locks `numberdb-sage.w3.lock`
# and contends only with other runs in that slot, which is how a worker gets a
# Sage instance of its own. The bound then lives where the hardware is known
# -- `agents/workers.sh` sizes the pool to the machine and hands each worker
# its slot -- rather than here, where it is one for everybody for ever.
#
# Unset means the shared lock, so nothing that does not opt in can start a
# second Sage beside a run that is already going.
LOCK="/tmp/numberdb-sage${NUMBERDB_SAGE_SLOT:+.$NUMBERDB_SAGE_SLOT}.lock"


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

run_id="$(date +%s)-$$-${RANDOM:-0}"
remote_dir="/tmp/agent-run-$run_id"
mounts=()
for file in "$@"; do
	[ -f "$file" ] || { echo "no such file: $file" >&2; exit 2; }
	base=$(basename "$file")
	put_there "$file" "$remote_dir.$base"
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
run_there_quietly "chmod 644 $remote_dir.* 2>/dev/null || true"

cleanup() {
	#The container as well as the copies. A `timeout` on this side kills the
	#local ssh and leaves the remote work running, and an abandoned Sage
	#process is what takes the machine down.
	run_there_quietly "rm -rf $remote_dir.*; docker rm -f '$name' >/dev/null 2>&1" \
		>/dev/null 2>&1 || true
}
trap cleanup EXIT

# --no-deps so this never restarts the site's own containers.
# Polled rather than blocked, and the wait is said out loud every minute.
#
# `flock -w 3600` waits in silence, and silence is the one thing a run cannot
# afford: four workers share this box, so a Sage call may queue behind
# another worker's -- and an agent watching a command that has printed
# nothing for ten minutes is an agent about to decide something. A line a
# minute keeps the command visibly alive, and twenty minutes is long enough
# for any generator here (the worst measured is three minutes a value) and
# short enough that a wedged lock is reported rather than waited out.
#
# The original note, still true of why there is a lock at all:
# `flock -w` waits rather than failing outright: a queued run is what somebody
# wants, and a refusal would only be retried by hand. `--rm` and a name let the
# cleanup below reach the container if this end dies first, which is the other
# half of the problem -- `timeout` here kills the ssh, never the work.
# What a run may take before Docker stops it, measured rather than guessed.
#
# A run's memory is almost all fixed cost and almost none of it the numbers:
#
#   * importing Sage            98 MB, every run, before it computes anything
#   * the erf generator        100 MB total -- all 1001 values cost 1 MB and
#                              under a second between them; the values hold
#                              133 KB of text
#   * the newform generator    211 MB, of which 91 MB is building the Hecke
#                              orbits and the PARI cross-check in `enumerate`;
#                              its 686 polynomials cost nothing measurable
#   * one killed on 2026-09-11  386 MB
#
# The server has about 350 MB available at rest, with the site's own worker at
# 183 MB and 420 MB already in swap. So one build is the whole of the free
# memory, and a build that wants a little more takes the site down with it --
# three times on 2026-09-11, the kernel choosing what to kill.
#
# 320 MB fits every run measured with half as much again to spare, and stops
# one heading for 386 MB. `--memory-swap` equal to `--memory` means the
# container gets no swap at all: it dies instead of dragging the machine into
# the thrashing, which is the whole point. A failed build is cheap and says so
# in the log; an unreachable server is neither.
#
# Raise it for a run known to need more, when nothing else is on:
#
#     NUMBERDB_SAGE_MEMORY=600m agents/sage.sh ...
#
# `docker run` rather than `docker compose run`, which has no resource flags
# at all -- a cap added as `--memory` there did not limit anything, it refused
# every run with "unknown flag". It also means a builder needs no compose file
# and no checkout of the site: an image and a docker daemon are the whole of
# it.

name="numberdb-agent-run-$run_id"
run_there \
	"exec 9>'$LOCK'; \
	 waited=0; \
	 until flock -n 9; do \
		if [ \$waited -ge ${LOCK_WAIT:-1200} ]; then \
			echo 'the Sage box has been busy for twenty minutes; try again' >&2; \
			exit 75; \
		fi; \
		[ \$((waited % 60)) -eq 0 ] && echo \"waiting for the Sage lock: another worker is using it (\${waited}s)\" >&2; \
		sleep 15; waited=\$((waited + 15)); \
	 done; \
	 timeout $TIMEOUT docker run --rm -i --name '$name' \
		--memory='$MEMORY' --memory-swap='$MEMORY' \
		${pythonpath[*]} \
		-e NUMBERDB_ASSISTED_BY='${NUMBERDB_ASSISTED_BY:-assisted by an agent}' \
		-e NUMBERDB_KEY_FROM_STDIN='${NUMBERDB_KEY_FROM_STDIN:-0}' \
		-e NUMBERDB_PUBLISH='${NUMBERDB_PUBLISH:-0}' \
		-e NUMBERDB_RESTATING='${NUMBERDB_RESTATING:-0}' \
		-e NUMBERDB_LOWERING='${NUMBERDB_LOWERING:-0}' \
		${mounts[*]} \
		--entrypoint sage \
		'$IMAGE' -python -u /work/$(basename "$main")" \
	2>&1 | grep --line-buffered -viE 'collecting static|static files copied|Starting command as|^ Container |remote port forwarding'
#`-u` and `--line-buffered`: without them a run that is killed at its
#timeout shows only whole 4 KB blocks of what it printed, and three runs of
#the lattice checks on 2026-09-05 each stopped at the same block boundary,
#so nothing said which step had stalled.
