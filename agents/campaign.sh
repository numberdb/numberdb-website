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
#Attempts at the table currently being built. Policy, not judgement: however
#good a reason triage gives, the same table is not tried a third time.
attempted=0

batch_file() {
	ls -t agents/table-ideas/BATCH-*.md 2>/dev/null | head -1
}

propose_a_batch() {
	agents/run.sh ideas "Propose a batch from the open 'table wanted' issues, screening every candidate, in an area the corpus does not already cover. Write it to agents/table-ideas/BATCH-$(date -u +%Y-%m-%dT%H%M).md and commit it."
}

say() { printf '\n=== %s\n' "$*"; }

while [ "$made" -lt "$builds" ]; do
	#Asked for between tables, so a campaign can be stopped without killing a
	#build half-way. Twice I stopped one by killing the process, and both
	#times the build in flight died with it: the parent's children are not
	#spared, and a run that was twenty minutes in was simply lost.
	#
	#    touch agents/campaign.stop
	if [ -e agents/campaign.stop ]; then
		say "stopping: agents/campaign.stop is there"
		rm -f agents/campaign.stop
		exit 0
	fi

	if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
		say "stopping: the tree has uncommitted changes"
		git status --short --untracked-files=no
		exit 3
	fi

	batch=$(batch_file)
	if [ -z "$batch" ]; then
		say "no batch yet; proposing one"
		propose_a_batch || exit $?
		continue
	fi

	say "next table from $(basename "$batch") (built $made so far)"
	before=$(git rev-parse HEAD)
	#`$?` inside `if ! cmd` is the status of the negation, not of the command,
	#so this used to report "the build run exited 0" and then exit 0 -- a
	#failed campaign that looked like a finished one. It said exactly that
	#when an expired OAuth token stopped a build on 2026-09-03.
	status=0
	agents/run.sh build "Build the highest-ranked proposal in $batch that no generator in generators/ answers yet. Say at the start which one you chose and why it is the next one. Follow the order of work in the prompt. Do not publish. If every proposal in that batch is already built, say so and stop without building anything, and do not commit." || status=$?
	if [ "$status" -ne 0 ]; then
		#What to do about a failure is a judgement, and it has been made four
		#times today by a line of shell and been wrong each time: HEAD moving
		#always, `T182` inside a run stamp, `subtype` saying success on a 401,
		#and a grep for `api_error_status` that cannot tell a run which died
		#on turn 1 from one which died on turn 39 with a draft half filled.
		#
		#So it is asked of something that can look. What stays here is what is
		#policy rather than judgement: one attempt per table, and the token
		#refreshed first -- if the failure was the eight-hour boundary, the
		#triage run shares that credential and cannot start either.
		stamp=$(ls -t agents/runs/*-build.log 2>/dev/null | head -1 \
		        | xargs -r basename 2>/dev/null | sed 's/-build.log$//' || true)
		verdict=stop
		if [ -n "$stamp" ] && [ "$attempted" -lt 2 ]; then
			timeout 120 claude -p "Reply with exactly: ok" >/dev/null 2>&1 || true
			say "the build run exited $status; asking what to do about it"
			agents/run.sh triage "The build run $stamp failed with status $status. Its log is agents/runs/$stamp-build.log and the campaign was at $before before it. Decide what happens next and write agents/runs/$stamp-verdict." \
				|| say "the triage run failed too"
			if [ -f "agents/runs/$stamp-verdict" ]; then
				verdict=$(head -1 "agents/runs/$stamp-verdict" | tr -d '[:space:]')
			fi
		fi
		say "verdict: $verdict"
		case "$verdict" in
			resume)
				attempted=$((attempted + 1))
				session=$(awk -F'\t' -v s="$stamp" '$1 == s {print $10}' \
				          agents/runs/COSTS.tsv | tail -1)
				if [ -z "$session" ]; then
					say "stopping: no session recorded for $stamp to resume"
					exit "$status"
				fi
				NUMBERDB_RESUME="$session" agents/run.sh build "Continue where you left off." \
					|| { say "stopping: the resumed run failed too"; exit 1; }
				;;
			restart)
				attempted=$((attempted + 1))
				continue
				;;
			skip)
				attempted=0
				say "skipped; see agents/table-ideas/SKIPPED.md"
				continue
				;;
			*)
				say "stopping: $verdict"
				exit "$status"
				;;
		esac
	else
		attempted=0
	fi

	#Did it build anything? A build that built a table commits a generator for
	#it, so that is the question to ask. It used to ask whether HEAD had moved,
	#which looks equivalent and is not: `run.sh` commits its own COSTS.tsv line
	#at the end of every run, so HEAD moves even when the agent built nothing
	#and said so. On 2026-09-03 the exhausted BATCH-2026-09-02 was answered by
	#a six-turn run costing $0.95 that correctly built nothing, and the loop
	#read the cost commit as a table.
	#
	#The generator is also where the T-number comes from below, so the two
	#questions have one answer.
	generator=$(git diff --name-only "$before"..HEAD -- generators/ \
	            | grep -E 'generate\.py$' | head -1 || true)
	if [ -z "$generator" ]; then
		say "$(basename "$batch") is finished; proposing the next batch"
		before_batch=$(git rev-parse HEAD)
		propose_a_batch || exit $?
		if [ "$(git rev-parse HEAD)" = "$before_batch" ]; then
			say "stopping: the stage-one run committed nothing either"
			exit 4
		fi
		continue
	fi
	made=$((made + 1))

	#Read the table as a reader would, in a session that did not build it.
	#The build checked its own numbers and cannot see its own prose; three
	#faults this year lived only in the rendered page. It reports and changes
	#nothing, so a critique that goes wrong costs a file nobody acts on.
	#The table's number, from the generator the build just committed: its
	#docstring names it on the first line ("... -- numberdb.org/T135"), a
	#convention every generator in the corpus follows. Nothing here may be
	#fatal -- `grep` finding nothing exits 1, and under `set -euo pipefail`
	#that killed a campaign inside a command substitution after a build it had
	#paid $10.43 for, with no message. Two cheaper guesses were tried on a real
	#transcript and both were wrong: the highest T-number mentioned gives T139,
	#and without word boundaries the run stamp 20260902T182455Z gives T182.
	tid=$(grep -aoE '\bT[0-9]{2,4}\b' "$generator" | head -1 || true)
	if [ -z "$tid" ]; then
		say "no T-number in $generator; skipping the critique and the repair"
	fi
	if [ -n "$tid" ]; then
		say "reading $tid as a reader would"
		agents/run.sh critique "Read $tid. Fetch the rendered page, read the document, run audit_table on it, and write agents/critiques/$tid.md. Change nothing else." \
			|| say "the critique run failed; the table stands and somebody should look"

		#Stage four acts on what stage three found, having checked it first.
		#Kept apart from the critique on purpose: a reader who may not change
		#anything reads differently from one who is about to, and the ten
		#critiques written by hand needed judgement four times -- two findings
		#already fixed, one claim that had to be narrowed, three that had to be
		#run before they could be written.
		#
		#Safe to leave unattended because an operated account's edits are never
		#published as reviewed: whatever it writes waits in the queue.
		say "acting on the critique of $tid"
		agents/run.sh repair "Act on agents/critiques/$tid.md, for $tid. Check every finding against the live table before you change anything, verify what can be verified, and write agents/critiques/$tid-repaired.md saying what you did with each." \
			|| say "the repair run failed; the critique stands and somebody should read it"
	fi

	#The ceiling is the intended stopping point and it announces itself: the
	#API refuses the create, the run says so in its report, and `run.sh`
	#returns what the agent returned. There is deliberately no probe here --
	#the obvious one, trying to create a draft, would leave a junk table
	#behind on every pass, which is a poor way to ask a question.
done

say "made $made table(s)"
