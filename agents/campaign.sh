#!/usr/bin/env bash
# Work through a batch of proposals, one table at a time, and propose a new
# batch when it runs out.
#
#     agents/campaign.sh                  # until the draft ceiling stops it
#     agents/campaign.sh 3                # at most three builds
#
# Everything here already existed; this only sequences it. One run at a time,
# because `agents/sage.sh` holds a lock and this machine has 961 MB.
#
# It stops, on purpose, at any of:
#
#   * the draft ceiling -- the API refuses a sixteenth unpublished draft, and
#     that refusal is the signal that somebody should read what is waiting
#   * a run that fails, because the next one would build on it
#   * a dirty tree, for the same reason `run.sh` refuses one
#   * the limit given as an argument
#
# What it does not do is decide anything. Which proposals exist is stage one's
# business, and whether a table is any good is a person's.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

builds="${1:-999}"
made=0

batch_file() {
	ls -t agents/table-ideas/BATCH-*.md 2>/dev/null | head -1
}

remaining_proposals() {
	#Proposals in the newest batch that no generator directory answers yet.
	local batch; batch=$(batch_file)
	[ -n "$batch" ] || { echo 0; return; }
	grep -c '^## [0-9]' "$batch" 2>/dev/null || echo 0
}

built_from() {
	#How many of them have been built, counted by the drafts and tables whose
	#generator sits in this repository. Crude on purpose: the exact accounting
	#is in the batch file, which a person reads.
	ls -d generators/*/ 2>/dev/null | wc -l
}

say() { printf '\n=== %s\n' "$*"; }

while [ "$made" -lt "$builds" ]; do
	if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
		say "stopping: the tree has uncommitted changes"
		git status --short --untracked-files=no
		exit 3
	fi

	batch=$(batch_file)
	if [ -z "$batch" ]; then
		say "no batch yet; proposing one"
		agents/run.sh ideas "Propose a batch from the open 'table wanted' issues, screening every candidate. Write it to agents/table-ideas/BATCH-$(date -u +%Y-%m-%d).md and commit it." || exit $?
		continue
	fi

	say "next table from $(basename "$batch") (built $made so far)"
	if ! agents/run.sh build "Build the highest-ranked proposal in $batch that no generator in generators/ answers yet. Say at the start which one you chose and why it is the next one. Follow the order of work in the prompt. Do not publish. If every proposal in that batch is built, say so and stop without building anything."; then
		status=$?
		say "stopping: the build run exited $status"
		exit "$status"
	fi
	made=$((made + 1))

	#The ceiling is the intended stopping point and it announces itself: the
	#API refuses the create, the run says so in its report, and `run.sh`
	#returns what the agent returned. There is deliberately no probe here --
	#the obvious one, trying to create a draft, would leave a junk table
	#behind on every pass, which is a poor way to ask a question.
done

say "made $made table(s)"
