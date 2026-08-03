#!/usr/bin/env bash
# Copy the production .env into a Bitwarden secure note.
#
#     scripts/env-to-bitwarden.sh              # update the note
#     scripts/env-to-bitwarden.sh --check      # compare only, change nothing
#
# The server holds the only working copy of the configuration. A note in the
# vault is the answer to "the machine is gone", but a note updated by hand is a
# note that silently falls behind: over one session this file changed eight
# times, and a stale note restores a configuration that no longer works.
#
# Requires the Bitwarden CLI, which is not a system package:
#
#     npm install -g @bitwarden/cli
#     bw login                  # once
#
# The vault must be unlocked. Either export a session first,
#
#     export BW_SESSION=$(bw unlock --raw)
#
# or let this script prompt, which it does exactly once.
#
# Nothing is written to disk at any point: the file travels from ssh through a
# pipe into bw. A temporary file would linger in the shell's history of the
# filesystem long after the secrets in it had been rotated.

set -euo pipefail

REMOTE="${REMOTE:-linode}"
RPATH="${RPATH:-/opt/numberdb-website}"
ITEM_NAME="${ITEM_NAME:-numberdb.org production .env}"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

if ! command -v bw >/dev/null; then
	echo "The Bitwarden CLI is not installed." >&2
	echo "  npm install -g @bitwarden/cli && bw login" >&2
	exit 2
fi

status=$(bw status 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo unknown)
case "$status" in
	unauthenticated) echo "Not logged in. Run: bw login" >&2; exit 2 ;;
	locked)
		if [ -z "${BW_SESSION:-}" ]; then
			echo "Vault is locked; unlocking." >&2
			BW_SESSION=$(bw unlock --raw)
			export BW_SESSION
		fi ;;
	unlocked) : ;;
	*) echo "Cannot read Bitwarden status. Is 'bw' logged in?" >&2; exit 2 ;;
esac

#Otherwise a note edited in the browser is invisible here, and this would
#happily overwrite it with an older server state.
bw sync >/dev/null

echo "Reading $REMOTE:$RPATH/.env"
content=$(ssh -o BatchMode=yes "$REMOTE" "cat $RPATH/.env")
if [ -z "$content" ]; then
	echo "FAILED: the file came back empty; refusing to overwrite the note." >&2
	exit 1
fi
lines=$(printf '%s\n' "$content" | grep -c '^[A-Z_0-9]*=' || true)
if [ "$lines" -lt 10 ]; then
	echo "FAILED: only $lines settings found, expected 20 or more." >&2
	echo "Refusing to replace a good note with a truncated file." >&2
	exit 1
fi

existing=$(bw list items --search "$ITEM_NAME" 2>/dev/null || echo '[]')
#The script goes in -c and the data on stdin. Written as a heredoc plus a
#here-string it would redirect stdin twice, the data would win, and python
#would try to execute the JSON.
item_id=$(printf '%s' "$existing" | NAME="$ITEM_NAME" python3 -c '
import json, os, sys
name = os.environ["NAME"]
try:
    items = json.load(sys.stdin)
except Exception:
    items = []
for it in items:
    if isinstance(it, dict) and it.get("name") == name:
        print(it["id"]); break
')

if [ "$CHECK_ONLY" = 1 ]; then
	if [ -z "$item_id" ]; then
		echo "  no note named '$ITEM_NAME' exists yet"
		exit 1
	fi
	stored=$(bw get item "$item_id" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("notes") or "")')
	if [ "$stored" = "$content" ]; then
		echo "  note is up to date ($lines settings)"
		exit 0
	fi
	echo "  NOTE IS STALE: it differs from the server"
	echo "  server settings: $lines"
	diff <(printf '%s\n' "$stored" | grep -oE '^[A-Z_0-9]+' | sort) \
	     <(printf '%s\n' "$content" | grep -oE '^[A-Z_0-9]+' | sort) \
	     | sed 's/^/    /' || true
	echo "  (values are not compared here, only which settings exist)"
	exit 1
fi

if [ -n "$item_id" ]; then
	bw get item "$item_id" \
		| CONTENT="$content" python3 -c '
import base64, json, os, sys
item = json.load(sys.stdin)
item["notes"] = os.environ["CONTENT"]
sys.stdout.write(base64.b64encode(json.dumps(item).encode()).decode())
' | bw edit item "$item_id" >/dev/null
	echo "  updated note '$ITEM_NAME' ($lines settings)"
else
	NAME="$ITEM_NAME" CONTENT="$content" python3 -c '
import base64, json, os, sys
item = {"type": 2, "name": os.environ["NAME"], "notes": os.environ["CONTENT"],
        "secureNote": {"type": 0}, "favorite": False}
sys.stdout.write(base64.b64encode(json.dumps(item).encode()).decode())
' | bw create item >/dev/null
	echo "  created note '$ITEM_NAME' ($lines settings)"
fi

#Read back rather than trusting the write, since the whole point is that this
#copy is correct on a day when the server is not available to check against.
bw sync >/dev/null
stored=$(bw list items --search "$ITEM_NAME" \
	| NAME="$ITEM_NAME" python3 -c '
import json, os, sys
name = os.environ["NAME"]
for it in json.load(sys.stdin):
    if it.get("name") == name:
        print(it.get("notes") or ""); break
')
if [ "$stored" = "$content" ]; then
	echo "  verified: the vault now holds exactly what the server has"
else
	echo "  WARNING: what was read back does not match what was sent" >&2
	exit 1
fi
