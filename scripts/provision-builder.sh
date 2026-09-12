#!/usr/bin/env bash
# Turn a fresh Linux VM into a machine that can build tables.
#
#     scripts/provision-builder.sh user@1.2.3.4
#     NUMBERDB_REMOTE=builder NUMBERDB_SAGE_IMAGE=numberdb/builder:latest \
#         agents/sage.sh generators/<name>/generate.py
#
# Cloud-agnostic on purpose. A builder needs Docker and one image; it needs no
# checkout, no compose file, no database and no secrets -- `agents/sage.sh`
# scp's the scripts it wants to run and mounts them, and a generator publishes
# to numberdb.org over the public API like any outside contributor. So the
# same script provisions a VM on GCP, Azure, AWS, Hetzner or a spare laptop,
# and the only per-cloud part is the one command that creates the VM.
#
# Why a builder at all: two tables are stubs because SnapPy is not on the web
# server and should not be. T141 stops at ten crossings, T219 holds 2 of the
# closed census's 11,031 manifolds. A build-time dependency belongs on the
# machine that builds.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

TARGET="${1:-}"
[ -n "$TARGET" ] || { echo "usage: $0 <ssh target>   e.g. builder or user@host" >&2; exit 2; }
IMAGE="${NUMBERDB_SAGE_IMAGE:-numberdb/builder:latest}"

ssh_opts=(-o BatchMode=yes -o ConnectTimeout=30 -o ServerAliveInterval=15
          -o StrictHostKeyChecking=accept-new)

say() { printf '\n=== %s\n' "$*"; }

say "checking $TARGET answers"
ssh "${ssh_opts[@]}" "$TARGET" "uname -sr; nproc; free -m | sed -n 2p"

say "installing docker if it is not there"
# Docker's own convenience script: the distribution packages lag, and a build
# image pinned by digest deserves a daemon new enough to pull it.
ssh "${ssh_opts[@]}" "$TARGET" "command -v docker >/dev/null 2>&1 || { \
	curl -fsSL https://get.docker.com | sudo sh; \
	sudo usermod -aG docker \$(id -un) || true; }"

say "sending the build context"
# Only what the image needs: its Dockerfile and the client it installs.
tar cz deploy/docker/Dockerfile.build clients/python \
	| ssh "${ssh_opts[@]}" "$TARGET" \
	  "rm -rf ~/numberdb-builder && mkdir -p ~/numberdb-builder && tar xz -C ~/numberdb-builder"

say "building $IMAGE (this pulls Sage once, about 3 GB)"
ssh "${ssh_opts[@]}" "$TARGET" \
	"cd ~/numberdb-builder && sudo docker build -f deploy/docker/Dockerfile.build -t '$IMAGE' . 2>&1 | tail -5"

say "checking the image can do the thing it exists for"
ssh "${ssh_opts[@]}" "$TARGET" \
	"sudo docker run --rm --entrypoint sage '$IMAGE' -python -c \
	 \"import snappy, numberdb; print('snappy', snappy.version()); \
	   print('census', len(snappy.OrientableClosedCensus)); \
	   print('client ok')\""

say "done"
cat <<NOTE
Point runs at it with:

    NUMBERDB_REMOTE=$TARGET NUMBERDB_SAGE_IMAGE=$IMAGE \\
        agents/sage.sh <script.py> [more files to mount]

Nothing else moves. The lock, the timeout and the memory cap are the same,
and the site keeps serving while this machine computes.
NOTE
