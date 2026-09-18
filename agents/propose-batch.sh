#!/usr/bin/env bash
# The ideation job: screen a family of tables and put it in the queue.
#
#     agents/propose-batch.sh              # one family, whatever it judges best
#     NUMBERDB_MINER=codex agents/propose-batch.sh
#
# Separate from `campaign.sh` because the two jobs have nothing in common
# operationally. This one reads and screens: network, no Sage, no SnapPy,
# about thirteen minutes, and it can run on the cheapest machine there is. A
# build needs the heavy image and about forty minutes. One of these feeds five
# or six of those, so a campaign that stopped to screen was a build machine
# idling at $8.30 a time -- and a screening run that failed took a campaign
# with it.
#
# What it leaves behind, in three places that each have a reason:
#
#   * the batch file, on this disk, gitignored, because it is data
#   * a copy in `numberdb-runs/ideas/`, because this disk is not a backup and
#     one of these machines is an instance that can be terminated
#   * an issue in numberdb-data, labelled `proposal`, because that is the
#     queue every machine can read and the tracker the screening itself
#     searches when it asks what has already been asked for
#
# See `docs/design/where-ideas-live.md`.

set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

miner="${NUMBERDB_MINER:-${NUMBERDB_AGENT:-claude}}"
say() { printf '\n=== %s\n' "$*"; }

before=$(ls -t agents/table-ideas/BATCH-*.md 2>/dev/null | head -1 || true)

# Either harness can screen, so one account's exhausted quota hands the job
# to the other rather than ending the campaign that asked for it. `run.sh`
# exits 6 when it has spent every model its engine may use and the other
# engine is installed; see the same handover in agents/campaign.sh.
other=claude
if [ "$miner" = claude ]; then other=codex; fi
screen() {
	NUMBERDB_AGENT="$1" agents/run.sh ideas "Propose a batch from the open 'table wanted' issues, screening every candidate, in an area the corpus does not already cover. Write it to agents/table-ideas/BATCH-$(date -u +%Y-%m-%dT%H%M).md. Do not commit it: batches are data and .gitignore excludes them. Do not open an issue for it either; this job does that with what you wrote."
}

if ! screen "$miner"; then
	status=$?
	if [ "$status" -eq 6 ]; then
		say "$miner has no quota left; $other screens instead"
		screen "$other"
	else
		exit "$status"
	fi
fi

after=$(ls -t agents/table-ideas/BATCH-*.md 2>/dev/null | head -1 || true)
if [ -z "$after" ] || [ "$after" = "$before" ]; then
	say "the run proposed no new batch"
	exit 4
fi

# Never fatal: a batch that reached neither shelf is still on this disk, and
# saying where it is beats losing the run over a network fault.
agents/archive-run.sh "$after" ideas || true
python3 agents/queue.py post "$after" || {
	say "no issue for $after; run: python3 agents/queue.py post $after"
	exit 4
}
