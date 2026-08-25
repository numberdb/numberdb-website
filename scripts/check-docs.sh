#!/usr/bin/env bash
# Run every example in every document, against the live site.
#
# The examples reach numberdb.org, so this runs where the network is -- on the
# server, inside the web container, which is also the only machine here with
# SageMath. Set NUMBERDB_API_KEY first or the anonymous rate limit will stop
# it part way through and every later example will look broken.
#
#     scripts/check-docs.sh
#
# What it does not cover, and why: the curl examples in the API reference
# (they need a key with write access, and running them would write), and the
# generator sketches (they describe a shape rather than a table that exists).
# Those are marked in the pages themselves.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
remote="${NUMBERDB_HOST:-linode}"
key="$(grep -E '^NUMBERDB_API_KEY=' "$here/.env" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"'"' || true)"

if [ -z "$key" ]; then
	echo "No NUMBERDB_API_KEY in .env; the run will hit the anonymous limit." >&2
fi

bundle=$(mktemp -d)
trap 'rm -rf "$bundle"' EXIT
tar czf "$bundle/docs.tgz" -C "$here/clients/python" numberdb tests README.md
tar czf "$bundle/pages.tgz" -C "$here" README.md \
	numberdb_app/templates/help.html \
	numberdb_app/templates/api-reference.html \
	.claude/skills/numberdb-table/SKILL.md AGENTS.md

scp -q "$bundle/docs.tgz" "$bundle/pages.tgz" "$remote:/tmp/"
printf '%s' "$key" | ssh -o BatchMode=yes "$remote" 'read -r KEY || true
cd /opt/numberdb-website
docker compose exec -T web bash -lc "rm -rf /tmp/checkdocs"
rm -rf /tmp/checkdocs && mkdir /tmp/checkdocs
tar xzf /tmp/docs.tgz -C /tmp/checkdocs
mkdir -p /tmp/checkdocs/pages && tar xzf /tmp/pages.tgz -C /tmp/checkdocs/pages
cp /tmp/checkdocs/pages/README.md /tmp/checkdocs/repository-README.md
cp /tmp/checkdocs/pages/numberdb_app/templates/*.html /tmp/checkdocs/
cp /tmp/checkdocs/pages/.claude/skills/numberdb-table/SKILL.md /tmp/checkdocs/
cp /tmp/checkdocs/pages/AGENTS.md /tmp/checkdocs/
docker cp /tmp/checkdocs numberdb-website-web-1:/tmp/checkdocs >/dev/null
docker compose exec -T -e NUMBERDB_API_KEY="$KEY" web bash -lc "
cd /tmp/checkdocs
sage -python tests/check_documentation.py \
    README.md repository-README.md help.html api-reference.html \
    SKILL.md AGENTS.md
"'
