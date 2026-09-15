#!/usr/bin/env bash
# Put one run's transcript somewhere that is not this disk.
#
#     agents/archive-run.sh agents/runs/20260911T103426Z-build.log
#
# The transcripts are the record of what every table build, critique and
# repair actually did, and until now they lived in exactly one place:
# `agents/runs/` on one workstation, which `.gitignore` excludes and no backup
# covers -- `scripts/backup.sh` dumps the database and nothing else. 344 MB of
# history, one disk, 29 MB free on it. The cost figures survived only because
# `sync-costs.sh` imports them into Postgres, which the dump does carry.
#
# Uploaded through the GitHub contents API rather than a clone, so this works
# from a machine with no room and from a cloud job with no persistent disk --
# which is the case that makes it necessary rather than tidy, since a job's
# filesystem is gone the moment it exits.
#
# Never fatal. A transcript that did not reach the archive is worth a warning;
# it is not worth failing a build that produced a table.
set -uo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

REPO="${NUMBERDB_RUNS_REPO:-numberdb/numberdb-runs}"

# Authored by the org's agent account, whose work this is. The GitHub user
# `zeta3` is an unrelated person; the bot is `zeta3-bot`, id 79627455.
BOT_NAME="${NUMBERDB_BOT_NAME:-zeta3-bot}"
BOT_EMAIL="${NUMBERDB_BOT_EMAIL:-79627455+zeta3-bot@users.noreply.github.com}"

log="${1:-}"
#Transcripts go to `runs/`, and a batch of proposals to `ideas/`: the same
#upload, a different shelf. A batch is the more valuable of the two per byte
#-- a transcript records what one run did, a batch is a screened plan that
#several runs will work from -- and until now it was the one not archived.
dir="${2:-runs}"
[ -n "$log" ] || { echo "usage: $0 <file> [directory in the archive]" >&2; exit 2; }
[ -f "$log" ] || { echo "archive: no such file: $log" >&2; exit 0; }

command -v gh >/dev/null 2>&1 || {
	echo "archive: no gh on this machine; $log stays local" >&2; exit 0; }

name=$(basename "$log")
python3 - "$log" "$REPO" "$dir/$name.gz" "$BOT_NAME" "$BOT_EMAIL" <<'PY' || \
	echo "archive: $name did not reach $REPO; it is still here" >&2
import base64, gzip, json, subprocess, sys

path, repo, target, name, email = sys.argv[1:6]

#Compressed in memory: the machines this runs on are short of disk, and a
#transcript gzips to about a quarter of its size.
with open(path, "rb") as handle:
    blob = gzip.compress(handle.read(), 6)

who = {"name": name, "email": email}
payload = {"message": "archive %s" % target.rsplit("/", 1)[-1][:-3],
           "content": base64.b64encode(blob).decode("ascii"),
           "author": who, "committer": who}

done = subprocess.run(
    ["gh", "api", "-X", "PUT", "%s/contents/%s" % ("repos/" + repo, target),
     "--input", "-"],
    input=json.dumps(payload), capture_output=True, text=True)

if done.returncode != 0:
    #Already there is success: this is re-runnable on purpose.
    if "sha" in (done.stderr or "") and "already exists" in (done.stderr or ""):
        print("archive: %s was already there" % target)
        raise SystemExit(0)
    print((done.stderr or done.stdout)[:300], file=sys.stderr)
    raise SystemExit(1)

print("archive: %s -> %s (%d KB)" % (path, target, len(blob) // 1024))
PY
exit 0
