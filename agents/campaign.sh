#!/usr/bin/env bash
# Work through the queue of screened proposals, one table at a time, and pay
# for a new screening when it runs low.
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

# Where critiques live, and why it can be somewhere else.
#
# The file is the memory: `work.py` offers a table for growth until
# `<tid>-growth.md` exists and for a sweep until `<tid>.md` does. With four
# workers in four worktrees that was four separate memories -- 352 growth
# questions went to about 115 tables and T293 was asked twelve times. One
# directory, shared, and the rule means what it says.
critiques="${NUMBERDB_CRITIQUES:-agents/critiques}"
export NUMBERDB_CRITIQUES="$critiques"
mkdir -p "$critiques"
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

# Run one stage, and hand it to the other harness if the first has no quota
# left.
#
# One engine's quota is not both engines' quota, and every stage here can be
# run by either -- that is what the three role variables are for. Until now an
# exhausted account stopped the campaign: on 2026-09-18 codex ran out, the
# runner fell back to a model the account cannot use at all, and the campaign
# died with sixteen tables still to build while claude sat idle.
#
# `run.sh` exits 6 when it has spent every model its engine may use *and* the
# other engine is installed. The role flips for the rest of the campaign,
# because a quota that is gone stays gone for hours, and re-learning that
# once per stage would cost a failed run each time.
run_stage() {                    # role variable, stage, task...
	local role="$1" stage="$2"; shift 2
	local engine other status
	eval "engine=\$$role"
	if NUMBERDB_AGENT="$engine" agents/run.sh "$stage" "$@"; then
		return 0
	fi
	status=$?
	[ "$status" -eq 6 ] || return "$status"
	#Written as an if, not as `[ ... ] && other=codex`: under `set -e` a test
	#that is simply false ends the campaign.
	if [ "$engine" = claude ]; then other=codex; else other=claude; fi
	say "$engine has no quota left; $other takes over as $role for the rest of this campaign"
	eval "$role=\"$other\""
	NUMBERDB_AGENT="$other" agents/run.sh "$stage" "$@"
}

# Which proposals this campaign works from.
#
# The queue is the `proposal` issues in numberdb-data: one per family, each
# with a checklist of the tables in it. `agents/queue.py` speaks it, and
# `docs/design/where-ideas-live.md` says why it is there rather than in the
# file the ideation stage writes. The short version is that the file was
# excluded by `.gitignore`, lived on one disk, and only the newest of its kind
# was ever read -- which stranded about 39 screened proposals, at $1.50 each.
#
# Pin a family when several campaigns run at once, so that two of them do not
# walk the same list:
#
#     NUMBERDB_FAMILY=141 agents/campaign.sh
#
# Unpinned, a campaign finishes the family it is in before taking the newest
# one with work left, because the tables of a family share machinery and
# cross-reference each other. Two campaigns that do collide lose a minute and
# nothing else: the claim is the draft, so the second build is refused the
# title and moves to the next proposal.
family="${NUMBERDB_FAMILY:-}"

# How many tables are waiting, or empty if the queue could not be read. The
# difference matters: zero means pay for a screening, and unreadable means
# stop, because a campaign that reads "zero" from a broken `gh` would pay for
# a screening every time round the loop.
# How many proposals are waiting, or nothing if GitHub could not be asked.
#
# `set -o pipefail` is on, so a queue.py that exits non-zero -- a rate limit,
# a network blip, four workers asking at once -- made this command
# substitution fail, and `set -e` then killed the campaign *silently*, in the
# middle of `top_up_if_low`, before the check below could say "the queue
# could not be read". Three workers died that way within a minute of each
# other and the logs' last line was the previous item.
#
# So the failure is tolerated here and reported by the caller, which can tell
# the difference between "nobody is waiting" and "nobody answered".
queue_waiting() {
	python3 agents/queue.py open 2>/dev/null \
		| awk '/ waiting$/ {print $1}' | tail -1 || true
}

# The next table, as JSON: family, title, batch, screened, waiting.
queue_next() {
	if [ -n "$family" ]; then
		python3 agents/queue.py next --family "$family" 2>/dev/null || true
	else
		python3 agents/queue.py next 2>/dev/null || true
	fi
}

# One field out of that JSON, without a jq that may not be installed.
field() {
	python3 -c 'import json,sys
try:
	print(json.loads(sys.argv[1])[sys.argv[2]])
except Exception:
	pass' "$1" "$2"
}

# Pay for a screening. The job that does it is `agents/propose-batch.sh`, so
# that a machine which only screens can run it alone -- and so that the
# archiving and the issue are done by a script rather than asked of the run.
# A run asked to file its own result sometimes argues with the instruction
# instead: one wrote a 580-line batch, said it would not force-add a gitignored
# file, and was right.
propose_a_batch() {
	NUMBERDB_MINER="$miner" agents/propose-batch.sh
}

# Keep the queue shallow but never empty. Shallow because a proposal is a
# claim about the corpus on the day it was screened and this corpus moves: of
# 89 proposals screened here in a fortnight, about 19 still had no table like
# them by the end of it. Never empty because a build machine waiting for a
# screening is a build machine doing nothing.
#
# Only screening that will be used is paid for: with two builds left to do and
# five tables waiting, another batch is five days of nobody's time.
top_up_if_low() {
	local waiting remaining low="${NUMBERDB_QUEUE_LOW:-8}"
	waiting=$(queue_waiting || true)
	if [ -z "$waiting" ]; then
		#Asked again before giving up: with four workers the commonest reason
		#is that GitHub refused one request, and a campaign that stops for
		#that has thrown away an hour of quota for a hiccup.
		sleep 20
		waiting=$(queue_waiting || true)
	fi
	if [ -z "$waiting" ]; then
		say "the queue could not be read twice (is gh logged in? rate limit?)"
		if [ -z "$(queue_next)" ]; then
			say "stopping: and there is no work waiting either"
			exit 8
		fi
		say "carrying on with the work already in hand"
		return 0
	fi
	remaining=$((builds - made))
	if [ "$waiting" -eq 0 ] \
	   || { [ "$waiting" -lt "$low" ] && [ "$remaining" -gt "$waiting" ]; }; then
		say "$waiting proposals waiting; screening another family"
		#A screening that fails is not the end of a campaign: demands, growth
		#and sweeps are work too, and the queue may be low only because the
		#other workers are holding claims.
		if ! propose_a_batch; then
			local status=$?
			say "the screening failed with status $status"
			if [ -z "$(queue_next)" ]; then
				say "stopping: no screening to be had and nothing waiting"
				exit "$status"
			fi
			say "carrying on with the work that is already waiting"
		fi
	fi
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

	#Critiques excepted, for the reason `run.sh` excepts them: this loop writes
	#a person's demand into one and then runs the stage that acts on it, so
	#counting that as an unfinished edit stops the campaign on its own input.
	if [ -n "$(git status --porcelain --untracked-files=no -- . ':(exclude)agents/critiques')" ]; then
		say "stopping: the tree has uncommitted changes"
		git status --short --untracked-files=no -- . ':(exclude)agents/critiques'
		exit 3
	fi

	#So each run's ledger line says which campaign and which batch it belonged
	#to. Work that produces no table -- a failed build, a triage, the ideas
	#run itself -- has no other name, and without one its cost had nowhere to
	#go and was dropped.
	export NUMBERDB_CAMPAIGN="$NAME"

	top_up_if_low
	#What to do next, of any kind: build a proposal, act on somebody's demand,
	#ask whether a small table can grow, or read one nobody has ever read.
	#`agents/work.py` decides; this loop only carries it out. One pipeline,
	#four sources of work, because all four end in the same two steps -- a
	#list of claims about one table, and an agent that checks each and acts.
	next=$(python3 agents/work.py next --done "$made" 2>/dev/null || true)
	if [ -z "$next" ]; then
		say "nothing waiting anywhere and no screening to be had; stopping"
		exit 6
	fi

	# The same item twice is a queue that is not being consumed, and the loop
	# cannot tell the difference between that and work. On 2026-09-19 a
	# demand had no "done" mark, so this loop repaired T293 twenty-six times
	# for $58 and built nothing; the spend looked exactly like progress.
	#
	# Policy, not judgement: whatever the reason, the second identical item
	# stops the campaign rather than paying for it again.
	this_item=$(printf '%s|%s|%s' "$(field "$next" kind)" \
		"$(field "$next" tid)" "$(field "$next" title)")
	if [ "$this_item" = "${last_item:-}" ]; then
		say "the queue offered the same item twice: $this_item"
		say "stopping: something is not marking work as done, and paying for it again would not help"
		exit 8
	fi
	last_item="$this_item"
	kind=$(field "$next" kind)
	tid=$(field "$next" tid)

	if [ "$kind" != proposal ]; then
		#Reviewing an existing table. The critique file is the interface: a
		#demand arrives with one already written (by work.py, carrying its
		#provenance), and growth and sweep need the question asked first.
		say "$kind: $tid -- $(field "$next" title) (done $made)"
		case "$kind" in
			growth)
				run_stage critic critique \
					"Read $tid, which has $(field "$next" entries) entries in $(field "$next" bytes) bytes -- under a tenth of the soft limits of 1200 entries and 320 KB. The question is whether it can grow *naturally*: is its range the whole of what its definition promises, or was it stopped early? Read the skill on what makes a good range, read the table's own completeness note and its generator, and write $critiques/$tid-growth.md saying either how far it could go and by what method, or why it is already complete -- a named constant with one entry is finished, and saying so is a good answer. Change nothing." \
					|| say "the growth question failed for $tid"
				;;
			sweep)
				run_stage critic critique \
					"Read $tid. Fetch the rendered page, read the document, run the audit on it, and write $critiques/$tid.md. This table has never been read by this pipeline -- most of the corpus below T127 was made by hand, before the skill existed -- so read it as a reader meeting it for the first time. Change nothing else." \
					|| say "the critique failed for $tid"
				;;
		esac

		report="$critiques/$tid.md"
		[ "$kind" = growth ] && report="$critiques/$tid-growth.md"
		if [ ! -f "$report" ]; then
			# Say so in the file the next campaign will look for.
			#
			# The report *is* the mark: `work.py` offers a table for growth
			# until `<tid>-growth.md` exists and for a sweep until
			# `<tid>.md` does. A run that produced neither left the table
			# exactly as it found it, so the queue offered it again, and the
			# repeat guard -- correctly -- stopped the campaign. Three
			# workers stopped that way on T293 within a minute.
			#
			# A note saying the question was asked and went unanswered is
			# both true and enough: a person reading the queue sees a table
			# nobody could report on, rather than a table nobody tried.
			say "no report at $report; writing down that the run produced none"
			mkdir -p "$critiques"
			{
				printf '# %s: the %s run produced no report\n\n' "$tid" "$kind"
				printf 'Asked on %s by campaign %s and the run ended without\n' \
					"$(date -u +%Y-%m-%d)" "$NAME"
				printf 'writing one. That is a fact about the run, not about the\n'
				printf 'table: somebody should look, and until then this file is\n'
				printf 'what stops the queue offering %s round and round.\n' "$tid"
			} > "$report"
			made=$((made + 1))
			continue
		fi
		run_stage writer repair \
			"Act on $report, for $tid. Check every finding against the live table before you change anything, verify what can be verified, and write ${report%.md}-repaired.md saying what you did with each." \
			|| say "the repair failed for $tid; the report stands and somebody should read it"
		made=$((made + 1))
		continue
	fi

	in_family=$(field "$next" family)
	proposal=$(field "$next" title)
	#Which batch this work came from, for the ledger. Not NUMBERDB_BATCH:
	#that one used to *pin* the batch, and exporting it here pinned a campaign
	#to its first batch for ever -- 21 tables of a campaign became 4, because
	#a stage-one run wrote six good proposals and the campaign kept reading
	#the old file. Telling the ledger where a run came from and telling the
	#campaign what to work on are two different sentences.
	export NUMBERDB_BATCH_NAME="$(field "$next" batch)"
	if [ -z "$in_family" ] || [ -z "$proposal" ]; then
		say "the queue answered something this cannot read: $next"
		exit 8
	fi

	# Claim it before spending anything, so that the worker beside this one
	# takes a different table. The checklist is the queue and a claim is a
	# `- [~]` on it, which `waiting()` has always skipped.
	#
	# Without this, two workers read the same checklist, pick the same first
	# unbuilt title and spend fifteen minutes each discovering that the other
	# took the draft -- the site refuses a duplicate title, which is safe and
	# wasteful. A claim that is never settled is cleared by `release` below,
	# or left as `- [~]` for a person if the campaign dies mid-build.
	if ! python3 agents/queue.py claim "$in_family" "$proposal" \
			--worker "$NAME" >/dev/null 2>&1; then
		say "could not claim $proposal in #$in_family; another worker has it"
		continue
	fi
	#Finish the family you are in. Set after the first build of a family, so
	#that a campaign started with no preference still picks up where the last
	#one stopped rather than opening a new family beside a half-built one.
	family="$in_family"

	say "next: $proposal (family #$in_family, built $made so far)"
	before=$(git rev-parse HEAD)
	#`$?` inside `if ! cmd` is the status of the negation, not of the command,
	#so this used to report "the build run exited 0" and then exit 0 -- a
	#failed campaign that looked like a finished one. It said exactly that
	#when an expired OAuth token stopped a build on 2026-09-03.
	status=0
	run_stage writer build "Build this table: $proposal. It is one of the family in numberdb-data issue #$in_family; read the family first with 'python3 agents/queue.py show $in_family', because the conventions its tables share are in it and the tables are meant to agree with each other. The screening is a claim about the corpus on the day it was made, so re-check the cheap half before you spend anything: already_here and already_asked from agents/table-ideas/screen.py, api/lookup on a few of the values you expect, and whether the tag it wants exists. If the corpus already holds this table, do not build it again: run 'python3 agents/queue.py built $in_family \"$proposal\" T<number>' with the number of the table that holds it, say so, and stop. If it should not be built for any other good reason -- the sources disagree about the definition, the data is not public, the family turns out not to be a table -- run 'python3 agents/queue.py skipped $in_family \"$proposal\" \"<the reason, in one line>\"' and stop; that is what keeps the next campaign from paying to reach the same conclusion. Otherwise claim it by creating its draft, as the prompt says: if the title is refused because it exists, that proposal is taken -- say so and stop, and the campaign will move on. Do not use the presence of a directory in generators/ to decide what is already built; another campaign may be building it in a tree you cannot see. Follow the order of work in the prompt. Do not publish." || status=$?
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
			run_stage critic triage "The build run $stamp failed with status $status. Its log is agents/runs/$stamp-build.log and the campaign was at $before before it. Decide what happens next and write agents/runs/$stamp-verdict." \
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
		#The build made nothing, and with a queue that no longer means the
		#proposals have run out: the campaign knew how many were waiting
		#before it spent anything. It means this proposal was declined -- the
		#corpus already holds it, or another campaign claimed the title first
		#-- and the build was asked to tick the box or say so.
		#
		#So the question is whether the queue moved. If it did, the decline
		#was orderly and the next table is a different one. If it did not,
		#the same proposal is about to be handed out again, and a loop that
		#pays $5.69 a time to be told the same thing is the expensive way to
		#learn it.
		empty=$((empty + 1))
		still=$(queue_next)
		if [ "$(field "$still" title)" = "$proposal" ] && [ "$empty" -ge 2 ]; then
			say "stopping: the build declined $proposal twice and the queue still offers it"
			say "read $transcript, and either build it by hand or close it in #$in_family"
			exit 6
		fi
		say "no table from that one; moving on"
		continue
	fi
	made=$((made + 1))
	#A table was built, so whatever the last decline meant, it is over.
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

	#Tick the box while the number is in hand. Not at the end of the campaign
	#and not by the agent: the campaign is the only party that knows both the
	#proposal it handed out and the table that came back, and a family whose
	#boxes are never ticked stays open for ever and is handed out again.
	if [ -n "$tid" ]; then
		python3 agents/queue.py built "$in_family" "$proposal" "$tid" \
			|| say "could not tick $proposal in #$in_family; do it by hand"
	else
		#Nothing was built, and the claim *stays*. Releasing it here is what
		#the loop did first, and the queue then offered the same proposal back
		#to the same worker on the next turn -- which the repeat guard read,
		#correctly, as nothing marking work as done, and stopped the campaign.
		#
		#A claim expires after ninety minutes, so the proposal is not lost: it
		#is out of this worker's way now and back in the queue for whoever is
		#free then, which is what "try it again later" means with four workers
		#and no memory between them. A proposal that should never be tried
		#again is a different thing and has its own mark: `queue.py skipped`,
		#which the build run is told to use.
		say "left $proposal claimed; it frees itself in ninety minutes"
	fi
	if [ -n "$tid" ]; then
		say "reading $tid as a reader would"
		run_stage critic critique "Read $tid. Fetch the rendered page, read the document, run audit_table on it, and write $critiques/$tid.md. Change nothing else." \
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
		run_stage writer repair "Act on $critiques/$tid.md, for $tid. Check every finding against the live table before you change anything, verify what can be verified, and write $critiques/$tid-repaired.md saying what you did with each." \
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

#Items of work, not tables: a growth question that found nothing to do and a
	#build that declined both count, and calling them tables made two workers
	#look as though they had built two hundred when between them they had
	#built a dozen.
	say "made $made item(s) of work"
