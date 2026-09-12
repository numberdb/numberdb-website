#!/usr/bin/env bash
# Work through a batch of proposals, one table at a time, and propose a new
# batch when it runs out.
#
#     agents/campaign.sh                  # until the draft ceiling stops it
#     agents/campaign.sh 3                # at most three builds
#
# Which engine does what, so that a weekly quota on one of them is not the end
# of the campaign, and so the pairing can be tried both ways round:
#
#     NUMBERDB_WRITER=codex  agents/campaign.sh   # codex builds and repairs
#     NUMBERDB_CRITIC=codex  agents/campaign.sh   # codex reads and judges
#     NUMBERDB_MINER=codex   agents/campaign.sh   # codex proposes the batch
#     NUMBERDB_AGENT=codex   agents/campaign.sh   # codex throughout
#
# The writer builds and repairs, the critic reads and triages, the miner
# proposes the batch. Each falls back to NUMBERDB_AGENT and then to claude, so
# the four writer/critic combinations are two variables.
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
# Batches in a row that produced no table. Reset by a build that makes one.
empty=0
# One engine per kind of work rather than one per campaign: the stages differ
# in what they are good at, and a reader who did not write the table is worth
# more when it is also not the same model.
default_engine="${NUMBERDB_AGENT:-claude}"
writer="${NUMBERDB_WRITER:-$default_engine}"
critic="${NUMBERDB_CRITIC:-$default_engine}"
miner="${NUMBERDB_MINER:-$default_engine}"
#Attempts at the table currently being built. Policy, not judgement: however
#good a reason triage gives, the same table is not tried a third time.
attempted=0

# Which proposals this campaign works from.
#
# Pinned per campaign when several run at once, because the only thing
# stopping two campaigns building the same table is that a build is told to
# skip proposals `generators/` already answers -- and two campaigns in two
# worktrees cannot see each other's generators. Different batches, no overlap.
#
#     NUMBERDB_BATCH=agents/table-ideas/BATCH-2026-09-11T1148.md
#
# Unset, it takes the newest, which is right when only one campaign is running.
batch_file() {
	if [ -n "${NUMBERDB_BATCH:-}" ]; then
		[ -f "$NUMBERDB_BATCH" ] || { echo "no such batch: $NUMBERDB_BATCH" >&2; exit 2; }
		echo "$NUMBERDB_BATCH"
		return
	fi
	#`|| true`, and it is not decoration. Under `set -euo pipefail` a glob
	#that matches nothing makes `ls` fail, `pipefail` carries that through
	#`head`, and `set -e` kills the campaign inside the command substitution
	#that called this -- with no message, because nothing was written. A fresh
	#clone has no batch file, since batches are data and are excluded, so the
	#first campaign on the AWS builder printed its header and vanished. On a
	#machine that has been building for a week there is always a batch, which
	#is why this survived that long.
	ls -t agents/table-ideas/BATCH-*.md 2>/dev/null | head -1 || true
}

propose_a_batch() {
	NUMBERDB_AGENT="$miner" agents/run.sh ideas "Propose a batch from the open 'table wanted' issues, screening every candidate, in an area the corpus does not already cover. Write it to agents/table-ideas/BATCH-$(date -u +%Y-%m-%dT%H%M).md. Do not commit it: batches are data and .gitignore excludes them."
}

say() { printf '\n=== %s\n' "$*"; }

# Is the site there? Every stage needs it -- the build writes a draft, the
# critique fetches the page, the repair reads the document -- and `run.sh`
# refuses with status 5 rather than spending anything when it is not.
#
# So an outage should make a campaign wait, not stop and not spend. On
# 2026-09-10 the server was down for half an hour and the campaign started a
# build against it, which is ten dollars to be told the site is not there.
site_is_up() {
	#Directly first, then through the tunnel.
	#
	#numberdb.org is blocked from the laptop this was written on and curl
	#reaches it only through a SOCKS proxy, so the proxy was the default --
	#which made the probe a statement about one machine's network. On a build
	#box with direct access and no tunnel, every probe failed and the campaign
	#sat waiting for a site that was answering perfectly well. It cost the
	#first run on the AWS builder.
	#
	#Trying direct first costs one request on the laptop and nothing anywhere
	#else, and neither machine needs to be told which it is.
	local url="${NUMBERDB_HOST:-https://numberdb.org}/skill"
	if curl -sS --max-time 20 -o /dev/null --noproxy '*' "$url" 2>/dev/null; then
		return 0
	fi
	local proxy="${ALL_PROXY:-${NUMBERDB_PROXY:-socks5h://127.0.0.1:1080}}"
	[ -n "$proxy" ] || return 1
	ALL_PROXY="$proxy" curl -sS --max-time 20 -o /dev/null "$url" 2>/dev/null
}

# Wait for it, and say so once rather than every minute. Returns 1 when the
# wait has gone on long enough that somebody should look: a site that has not
# come back in two hours is not a passing network fault.
wait_for_the_site() {
	local waited=0 limit="${NUMBERDB_OUTAGE_WAIT:-7200}" step=60
	site_is_up && return 0
	say "the site is not answering; waiting for it rather than spending a run"
	while ! site_is_up; do
		if [ "$waited" -ge "$limit" ]; then
			say "the site has not answered for $((limit / 60)) minutes; stopping"
			return 1
		fi
		sleep "$step"
		waited=$((waited + step))
	done
	say "the site answers again after $((waited / 60)) minute(s); carrying on"
	return 0
}

# What to call this campaign, so its stop flag and its log are its own.
NAME="${NUMBERDB_CAMPAIGN:-$(date -u +%Y%m%dT%H%M%SZ)}"

say "campaign $NAME: writer $writer, critic $critic, miner $miner"

while [ "$made" -lt "$builds" ]; do
	#Asked for between tables, so a campaign can be stopped without killing a
	#build half-way. Twice I stopped one by killing the process, and both
	#times the build in flight died with it: the parent's children are not
	#spared, and a run that was twenty minutes in was simply lost.
	#
	#    touch agents/campaign.stop            stops every campaign
	#    touch agents/campaign.$NAME.stop      stops this one
	#
	# Two files because two campaigns may be running: a global stop is
	# sometimes what you want and sometimes exactly not, and the first
	# campaign to notice used to delete the flag out from under the others.
	for flag in "agents/campaign.$NAME.stop" agents/campaign.stop; do
		if [ -e "$flag" ]; then
			say "stopping: $flag is there"
			#Only its own. The global one is left for the others to see and
			#for a person to remove, which is what makes it global.
			[ "$flag" = "agents/campaign.$NAME.stop" ] && rm -f "$flag"
			exit 0
		fi
	done

	#Before anything is spent on this table.
	wait_for_the_site || exit 7

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
	NUMBERDB_AGENT="$writer" agents/run.sh build "Build the highest-ranked proposal in $batch that the database does not already answer. Claim it first by creating its draft, as the prompt says: if the title is refused because it exists, that proposal is taken -- move to the next one. Do not use the presence of a directory in generators/ to decide what is already built; another campaign may be building it in a tree you cannot see. Say at the start which one you chose and why it is the next one. Follow the order of work in the prompt. Do not publish. If every proposal in that batch is already built, print the single line BATCH-EXHAUSTED and stop without building anything, and do not commit. Print that line only when you have checked every proposal in the batch and each one already has a table: it is what tells the campaign to spend money on a new batch, and a build that simply could not proceed must not print it." || status=$?
	if [ "$status" -ne 0 ] && { [ "$status" -eq 5 ] || ! site_is_up; }; then
		#Not a judgement at all: the site went away under the run. Asking
		#triage would spend a second run to be told the same thing, and
		#`run.sh` exits 5 from its own preflight without spending anything.
		#Wait for the site and build this table again.
		say "the run stopped because the site is unreachable, not because of the table"
		wait_for_the_site || exit 7
		continue
	fi

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
			NUMBERDB_AGENT="$critic" agents/run.sh triage "The build run $stamp failed with status $status. Its log is agents/runs/$stamp-build.log and the campaign was at $before before it. Decide what happens next and write agents/runs/$stamp-verdict." \
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
				NUMBERDB_RESUME="$session" NUMBERDB_AGENT="$writer" agents/run.sh build "Continue where you left off." \
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
	#Ask the site, not the working tree.
	#
	#A build claims its proposal by creating the draft, and the API answers
	#that with the table's number -- so the transcript of the run contains
	#`"tid": "T220"` exactly when a table was made, on whichever machine the
	#run happened, whether or not a generator was ever committed. That matters
	#now that `generators/` is a working copy rather than the record: the file
	#may not be tracked at all, and on a second machine it is certainly not in
	#*this* tree.
	#
	#The generator diff stays as a fallback for runs that predate this and for
	#anything the transcript does not name.
	transcript=$(ls -t agents/runs/*-build.log 2>/dev/null | head -1 || true)
	tid_from_run=""
	if [ -n "$transcript" ]; then
		tid_from_run=$(grep -aoE '"tid": *"T[0-9]{2,4}"' "$transcript" \
		               | grep -oE 'T[0-9]{2,4}' | head -1 || true)
	fi
	generator=$(git diff --name-only "$before"..HEAD -- generators/ \
	            | grep -E 'generate\.py$' | head -1 || true)
	if [ -z "$tid_from_run" ] && [ -z "$generator" ]; then
		#A build that made nothing is not the same as a batch that is
		#finished, and paying for a new batch is the expensive way to confuse
		#them. On 2026-09-12 the first campaign on the build machine spent
		#$24.56 doing exactly that: three stage-one runs at about $7.50 each,
		#alternating with builds that looked at the batch, judged every
		#proposal already built, and correctly stopped for under a dollar. No
		#table was made and nothing said anything was wrong.
		#
		#So: two in a row and the campaign stops. One is ordinary -- a batch
		#really can run out, and proposing the next one is the whole point of
		#that path. Two means the batches are not the problem, and the third
		#would cost another $7.50 to learn the same thing.
		#Which of the two happened? The build is asked to say. A batch that
		#really is used up prints BATCH-EXHAUSTED; a build that stopped for
		#any other reason prints nothing, and proposing a new batch would be
		#answering the wrong question at $7.50 a time.
		exhausted=no
		if [ -n "$transcript" ] && grep -aq 'BATCH-EXHAUSTED' "$transcript"; then
			exhausted=yes
		fi
		if [ "$exhausted" = no ]; then
			say "the build produced no table and did not say the batch was used up"
			say "not proposing another batch; read $transcript"
			exit 6
		fi

		empty=$((empty + 1))
		if [ "$empty" -ge 2 ]; then
			say "stopping: $empty batches in a row produced no table"
			say "the builds are refusing the proposals rather than running out of them; read $transcript"
			exit 6
		fi
		say "$(basename "$batch") is finished; proposing the next batch"
		#Whether a *new batch file exists*, not whether HEAD moved. Batches
		#are data and `.gitignore` has excluded them since the code and the
		#data were separated, so a stage-one run cannot commit one however
		#well it goes. On 2026-09-06 a run wrote a 580-line batch of five
		#proposals, said out loud that it would not force-add against that
		#decision, and was called a failure by this line: the campaign
		#stopped with a good batch sitting in the working tree.
		propose_a_batch || exit $?
		if [ "$(batch_file)" = "$batch" ] || [ -z "$(batch_file)" ]; then
			say "stopping: the stage-one run proposed no new batch"
			exit 4
		fi
		continue
	fi
	made=$((made + 1))
	#A table was built, so whatever the last empty batch meant, it is over.
	empty=0

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
	#The number the generator gives itself, "... -- numberdb.org/T164", and not
	#the first T-number in the file: T171's docstring omitted its own number and
	#mentioned T170 in a cross-reference, so a critique and a repair were spent
	#on a table finished an hour earlier. Failing that the highest number in the
	#file, which is the newest table and so almost always this one; failing that
	#nothing, and the loud skip below.
	#What the site said when the draft was created, first: it is the table
	#this run made, stated by the server, and it needs no file at all.
	tid="$tid_from_run"
	if [ -z "$tid" ] && [ -n "$generator" ]; then
		tid=$(grep -aoE 'numberdb\.org/T[0-9]{2,4}' "$generator" \
		      | grep -oE 'T[0-9]{2,4}' | head -1 || true)
	fi
	if [ -z "$tid" ] && [ -n "$generator" ]; then
		tid=$(grep -aoE '\bT[0-9]{2,4}\b' "$generator" \
		      | sort -t T -k2 -n | tail -1 || true)
	fi
	if [ -z "$tid" ]; then
		say "no table number in the transcript or the generator; skipping the critique and the repair"
	fi
	if [ -n "$tid" ]; then
		say "reading $tid as a reader would"
		NUMBERDB_AGENT="$critic" agents/run.sh critique "Read $tid. Fetch the rendered page, read the document, run audit_table on it, and write agents/critiques/$tid.md. Change nothing else." \
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
		NUMBERDB_AGENT="$writer" agents/run.sh repair "Act on agents/critiques/$tid.md, for $tid. Check every finding against the live table before you change anything, verify what can be verified, and write agents/critiques/$tid-repaired.md saying what you did with each." \
			|| say "the repair run failed; the critique stands and somebody should read it"
	fi

	#Offer it, whatever happened to the runs above.
	#
	#Offering is the last thing a build agent does, so a build that was
	#interrupted -- killed, or stopped when the site went away -- leaves a
	#finished table outside the review queue with no button to accept it, and
	#nothing afterwards notices. T210 sat there with 384 entries.
	#
	#The campaign knows the number and offering is idempotent, so it costs a
	#request and needs no judgement. The API refuses it for a table that is
	#already published or has no entries yet, which is the right answer in
	#both cases.
	if [ -n "$tid" ]; then
		ALL_PROXY="${ALL_PROXY:-${NUMBERDB_PROXY:-socks5h://127.0.0.1:1080}}" \
		curl -sS --max-time 30 -X POST \
			-H "Authorization: Bearer $(cat "${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}")" \
			"${NUMBERDB_HOST:-https://numberdb.org}/api/table/$tid/offer" \
			>/dev/null 2>&1 \
			&& say "$tid is offered for review" \
			|| say "could not offer $tid; it may already be published"
	fi

	#The ceiling is the intended stopping point and it announces itself: the
	#API refuses the create, the run says so in its report, and `run.sh`
	#returns what the agent returned. There is deliberately no probe here --
	#the obvious one, trying to create a draft, would leave a junk table
	#behind on every pass, which is a poor way to ask a question.
done

#What the runs learned, to wherever the rest of the work lives.
#
# A campaign on a build machine writes its lessons into that machine's
# checkout and they stay there: four from the first AWS campaign were only
# recovered by hand, and they are the one thing that campaign produced worth
# keeping. A campaign that cannot push says so rather than losing them
# quietly.
if [ -n "$(git status --porcelain agents/lessons/proposals 2>/dev/null)" ]; then
	git add agents/lessons/proposals 2>/dev/null || true
	git commit -q -m "lessons from campaign $NAME" -- agents/lessons/proposals \
		2>/dev/null || true
fi
if [ -n "$(git log --oneline @{u}..HEAD 2>/dev/null)" ]; then
	if git push -q 2>/dev/null; then
		say "pushed what this campaign learned"
	else
		say "could not push; the lessons of this campaign are only on this machine"
		git log --oneline @{u}..HEAD | sed 's/^/    /'
	fi
fi

say "made $made table(s)"
