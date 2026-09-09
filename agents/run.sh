#!/usr/bin/env bash
# Run one stage of the table pipeline in a fresh, unattended agent session.
#
#     agents/run.sh ideas                 # stage one: propose a batch
#     agents/run.sh build "proposal 1 of agents/table-ideas/BATCH-2026-08-30.md"
#     agents/run.sh repair "Act on agents/critiques/T136.md"
#     NUMBERDB_RESUME=<session> agents/run.sh build "..."   # continue a run
#
# The point of this file is that the session doing the work is not the session
# that asked for it. Everything the run needs -- the prompt, the environment,
# the key, the limits -- is set here rather than improvised there.
#
#   NUMBERDB_AGENT   claude (default) or codex
#   NUMBERDB_KEY     key file, default ~/.config/numberdb/zeta3-key
#   NUMBERDB_TURNS   turn limit, default 300
#
# What the run cannot do, and why it is safe to leave alone:
#
#   * it cannot publish a table. zeta3 may write and hold drafts; publishing is
#     board-only and enforced on the server, not by anything here.
#   * it cannot deploy. ship.sh refuses while NUMBERDB_AGENT_RUN is set.
#   * it cannot reach the container serving the site. Sage runs through
#     agents/sage.sh, in a throwaway.
#
# What it can do is commit to this repository and write to drafts, both of
# which are reversible and both of which a person reads afterwards.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

stage="${1:-}"
task="${2:-}"
case "$stage" in
	ideas) prompt_file="agents/table-ideas/PROMPT.md" ;;
	build) prompt_file="agents/table-build/PROMPT.md" ;;
	critique) prompt_file="agents/table-critique/PROMPT.md" ;;
	repair) prompt_file="agents/table-repair/PROMPT.md" ;;
	triage) prompt_file="agents/triage/PROMPT.md" ;;
	*) echo "usage: $0 {ideas|build|critique|repair|triage} [task]" >&2
	   exit 2 ;;
esac

engine="${NUMBERDB_AGENT:-claude}"
# Codex takes its model and its effort from the user's config unless it is
# told. A run says both out loud instead, so that the ledger records what
# actually answered rather than whatever the config happened to say that day,
# and so that the same campaign is the same campaign tomorrow.
codex_model="${NUMBERDB_CODEX_MODEL:-gpt-5.5}"
codex_effort="${NUMBERDB_CODEX_EFFORT:-xhigh}"
key_file="${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}"
turns="${NUMBERDB_TURNS:-300}"

[ -f "$prompt_file" ] || { echo "missing $prompt_file" >&2; exit 2; }
[ -f "$key_file" ] || { echo "no key at $key_file" >&2; exit 2; }
command -v "$engine" >/dev/null || { echo "no $engine on PATH" >&2; exit 2; }

# A run starts from a clean tree so that what it changed is what it committed,
# and a failed run can be thrown away with git.
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
	echo "Refusing: the tree has uncommitted changes." >&2
	git status --short --untracked-files=no >&2
	exit 3
fi

mkdir -p agents/runs
started=$(date -u +%Y%m%dT%H%M%SZ)
log="agents/runs/$started-$stage.log"

# numberdb.org is blocked from this network without the SOCKS proxy, and a
# plain curl to it hangs until it is killed rather than failing. curl and the
# client both honour ALL_PROXY, so setting it here means the run never has to
# know -- and the preflight below tests the same path the run will use.
export ALL_PROXY="${NUMBERDB_PROXY:-socks5h://127.0.0.1:1080}"
# But not the harness's own traffic. The proxy is here because numberdb.org is
# blocked from this network; chatgpt.com is not, and routing codex's control
# plane through it printed seven "failed to refresh available models" errors
# into the first run's log while the model itself answered perfectly well.
# Noise in a transcript is not free: it is the first thing read when a run
# goes wrong.
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}chatgpt.com,.chatgpt.com,openai.com,.openai.com"
export no_proxy="$NO_PROXY"
export NUMBERDB_AGENT_RUN=1
# What made this revision, at the granularity where it can change without
# anybody noticing: the harness, which agent, the version of that agent's
# prompt, and the run.
#
# Deliberately not the model. This is exported before the run and the CLI
# picks the model afterwards -- every campaign run so far has been
# claude-fable-5-1 while the record said "claude" -- so naming one here would
# be a claim this script cannot check. The model is read back from the
# transcript into COSTS.tsv below, where it is a fact rather than a guess.
#
# The prompt's own commit rather than HEAD: HEAD moves every run, because
# this script commits the cost line, and "which prompt was it running" is the
# question a reader of an old revision actually has.
#
# The phrase "assisted by" is not included: the client writes
# "<generator>, assisted by <this>", and putting it here produced "assisted
# by assisted by claude". The field is capped at 100 characters and that
# prefix spends about 45 of them, so there are roughly 50 to work with.
case "$engine" in
	claude) harness="Claude Code" ;;
	codex)  harness="Codex CLI" ;;
	*)      harness="$engine" ;;
esac
prompt_commit=$(git log -1 --format=%h -- "$prompt_file" 2>/dev/null || true)
prompt_version="$(basename "$(dirname "$prompt_file")")@${prompt_commit:-uncommitted}"
# Without the run stamp. It pointed into the run log and the cost ledger,
# which are data and no longer published, so on a public page it was a
# citation of something nobody outside can read. What is left resolves
# against this repository: the prompt's commit is here. The stamp is still
# written to the ledger, where it belongs and where it can be followed.
export NUMBERDB_ASSISTED_BY="$harness, $prompt_version"
export NUMBERDB_KEY_FILE="$key_file"

# And the key itself, for reading.
#
# The client takes `NUMBERDB_API_KEY` from the environment; it was given only
# the file's name, so every read went out anonymous -- 60 requests an hour
# against a corpus of 131 tables. A run would spend the budget walking the
# corpus, as the skill asks it to, and be refused ordinary lookups forty
# minutes later. Three runs met that before it was traced, and one wrote it
# down as the skill asking too much.
#
# In the environment rather than on a command line: `ps` shows arguments to
# everyone, `/proc/<pid>/environ` only to the same user, and this is the shape
# the client already reads. It never reaches a transcript.
export NUMBERDB_API_KEY="$(cat "$key_file")"

# The access token lasts eight hours and is refreshed when a process starts,
# not while one is running. A build takes half an hour to an hour and a half,
# so one that begins near the end of a window crosses it and dies on a 401
# mid-flight -- which happened twice on 2026-09-03. The second started at
# 16:57 with thirteen minutes of token left and died at 17:10, thirty-nine
# turns in, having spent most of a build.
#
# `expiresAt` is a timestamp, not a secret. A short call refreshes the token,
# which is what rewrote the credentials two minutes after that run died, so
# the fix is to make that call deliberately before a long one rather than by
# accident afterwards.
token_minutes_left() {
	python3 - <<'TOKEN' 2>/dev/null || echo unknown
import json, os, time
try:
	with open(os.path.expanduser('~/.claude/.credentials.json')) as handle:
		at = json.load(handle)['claudeAiOauth']['expiresAt']
except Exception:
	print('unknown')
else:
	seconds = at / 1000 if at > 1e11 else at
	print(int((seconds - time.time()) / 60))
TOKEN
}

# Not for triage, which is short and whose whole job is to run when
# something else has gone wrong. Blocking it on the same floor left a failed
# build with no verdict, and the campaign stopped without ever asking.
if [ "$engine" = "claude" ] && [ "$stage" != "triage" ]; then
	floor="${NUMBERDB_TOKEN_FLOOR:-90}"
	#Below this a run would die almost at once, and resuming would meet the
	#same wall, so there is nothing to be gained by starting.
	hard="${NUMBERDB_TOKEN_HARD_FLOOR:-15}"
	left=$(token_minutes_left)
	if [ "$left" != "unknown" ] && [ "$left" -lt "$floor" ] 2>/dev/null; then
		echo "=== $left minutes of token left, under the $floor-minute floor; refreshing"
		timeout 120 claude -p "Reply with exactly: ok" >/dev/null 2>&1 || true
		left=$(token_minutes_left)
		if [ "$left" != "unknown" ] && [ "$left" -lt "$hard" ] 2>/dev/null; then
			echo "Refusing: $left minutes of token left, under the $hard-minute" >&2
			echo "hard floor, and the refresh did not take. Re-authenticate" >&2
			echo "with 'claude auth login'." >&2
			exit 6
		fi
		if [ "$left" != "unknown" ] && [ "$left" -lt "$floor" ] 2>/dev/null; then
			#The refresh does not take at will: the CLI renews the token when
			#it needs to, not when asked, so between the floor and its own
			#threshold there is a window where nothing can be done about it.
			#Refusing there blocked every run for an hour and a quarter --
			#worse than the failure it was guarding against, now that a run
			#that crosses the boundary is resumable and triage will say so.
			echo "=== still $left minutes; starting anyway, and the run is resumable"
		else
			echo "=== refreshed; $left minutes now"
		fi
	fi
fi

# A run that cannot reach what the prompt requires should stop now rather
# than spend an hour and ten dollars finding out. Each of these is something
# the prompt tells the run to do.
for probe in "gh auth status" "curl -sS -o /dev/null https://numberdb.org/skill"; do
	if ! timeout 60 bash -c "$probe" >/dev/null 2>&1; then
		echo "Refusing: \`$probe\` does not work here, and the run needs it." >&2
		exit 5
	fi
done
probe=$(mktemp /tmp/numberdb-preflight-XXXXXX.py)
printf 'import numberdb\nfrom sage.all import RealBallField\nassert hasattr(numberdb, "table")\nprint("ok", RealBallField(32)(2).sqrt())\n' > "$probe"
if ! timeout 600 agents/sage.sh "$probe" >/dev/null 2>&1; then
	rm -f "$probe"
	echo "Refusing: agents/sage.sh cannot run, and every computation needs it." >&2
	exit 5
fi
rm -f "$probe"


briefing=$(cat <<BRIEF
$(cat "$prompt_file")

---

## How this run is set up

You are running unattended. Nobody will answer a question, so where the prompt
above says to stop and say so, write it down and stop -- that is a result.

**Sage.** Run every Sage computation with \`agents/sage.sh script.py\`. Do not
invent your own docker or ssh command: the container serving the site is not a
test environment, and running there has taken the site down before.

**The API key** is in the file named by \`NUMBERDB_KEY_FILE\`. Pipe it into
what needs it; never pass it as an argument, never print it, and never write it
into a file in this repository. \`agents/sage.sh\` forwards stdin, so
\`cat "\$NUMBERDB_KEY_FILE" | agents/sage.sh fill.py\` is the shape.

**You write as zeta3**, a program's account. It may write to tables and hold up
to five drafts. It may not publish and may not review; do not try, and do not
ask anybody to. Leaving a draft offered for review is a finished job.

**Do not deploy.** \`scripts/ship.sh\` will refuse anyway. \`ssh\`,
\`scp\`, \`docker\` and \`git push\` are refused too; \`agents/sage.sh\` is
how you reach the server.

**Finish before you stop.** Do not end your turn while a computation you
started is still running -- wait for it and use the answer. A previous run
ended with "waiting on the Sage checks" and its work was lost. If you are
running out of turns, write down what you have and commit that.

**Keep scratch out of the repository.** Working scripts go in \`/tmp\`. What
belongs in the repository is the batch, a generator you intend to keep, and a
lesson.

**Commit** each change as you make it, with a message saying what you learned
rather than what you touched. Do not push. **Never add a \`Co-Authored-By\`
trailer or any other AI attribution to a commit** -- this project does not use
them, and the first unattended run tried to.

**Work from the database and the issues, not from other people's transcripts.**
If something you need is unreachable, say so in your output and carry on with
what you have. Do not go looking through \`~/.claude\` for cached copies of it;
the first run spent twenty turns doing that and found nothing.

**When something you met is not in the skill**, write it down -- but sort it
first, because two different files are involved and mixing them spoils the
skill.

The skill is published at <https://numberdb.org/skill> for somebody who has
Python, and perhaps Sage or passagemath, and wants to contribute a table. Ask:
**could that person, on their own laptop, hit this?**

* Yes -- the mathematics of checking a value, what the API accepts, what the
  client returns, how search behaves, what a Sage import does not bring with
  it: append it to \`agents/lessons/PROPOSALS.md\`, in the format given there.
* No -- anything about this deployment: containers, ssh, the proxy,
  \`agents/sage.sh\`, your own permissions, a bug in the site itself: append it
  to \`docs/agent-environment.md\` instead. It is a real finding and worth
  writing down; it is just not a lesson about making tables.

Do not edit the skill itself: a person promotes a lesson, together with a
test.

## Your task

${task:-Follow the prompt above.}
BRIEF
)

# The tree as it stands before the agent touches it. `run.sh` refuses to start
# on uncommitted *tracked* changes but says nothing about untracked files, so
# a previous run's leftovers are here at the start -- and the check at the end
# must not blame this run for them.
tree_before=$(git status --porcelain --untracked-files=normal | sort)
# And where the history stood, so that what this run committed can be told
# from what was already here. A build learns which table it made from the
# generator it commits, and the first attempt at that read `$before` -- a
# variable belonging to campaign.sh, unset here, swallowed by `|| true`. So
# no build has ever been attributed to its table, which is the stage that
# costs the most.
head_before=$(git rev-parse HEAD)

echo "=== $stage run $started, engine $engine" | tee "$log"

# `set -e` would abort here the moment the agent exits non-zero: before
# the status is captured, before the ledger is written, before the commit
# that lets the next run start on a clean tree. So a run that failed left
# no record at all. A build died 39 turns in on an expired token on
# 2026-09-03, having cost real money, and the ledger has no row for it.
# What a failure cost is exactly the number worth keeping.
#
# Off around the call only, and PIPESTATUS[0] is read immediately after,
# so it is the agent's status and not tee's.
# The session is chosen here rather than read out of the transcript
# afterwards, because the transcripts are not kept and the ledger is: a run
# from last week is still resumable after its log is gone.
# Claude is told which session to be. Codex mints its own thread id and
# announces it in the first event it prints, so for codex this stays empty
# until the run has started and is read back out of the log afterwards.
session=""
if [ "$engine" = "claude" ]; then
	session="$(python3 -c 'import uuid; print(uuid.uuid4())')"
fi
if [ -n "${NUMBERDB_RESUME:-}" ]; then
	session="$NUMBERDB_RESUME"
	echo "=== resuming session $session"
fi

agent_status=0

run_agent() {
	# `start` or `resume`; each engine spells resuming its own way, and the
	# flags differ enough that composing one list for both is how the codex
	# branch came to be handed `--session-id`, which it does not know.
	local mode="$1"
	case "$engine" in
		claude)
			local flags=(--session-id "$session")
			[ "$mode" = "resume" ] && flags=(--resume "$session")
			# An allowlist of command prefixes does not survive contact with a
			# shell: the run composed `(curl ...; curl ...)`, `which a b c && ...`
			# and `sed -i ...`, none of which match a prefix, and nine commands
			# were refused for shape rather than for substance. So Bash is allowed
			# and the few things that could do harm are denied by name.
			#
			# This is a guard against drift, not against an adversary -- anything
			# here can be worked around by a run that means to. What cannot be
			# worked around is on the server: zeta3 may not publish, whatever it
			# runs locally.
			claude -p "$briefing" \
				--permission-mode acceptEdits \
				--allowed-tools \
					"Bash" "Read" "Write" "Edit" "Glob" "Grep" "WebFetch" "TodoWrite" \
				--disallowed-tools \
					"Bash(ssh:*)" "Bash(scp:*)" "Bash(rsync:*)" "Bash(docker:*)" \
					"Bash(git push:*)" "Bash(scripts/ship.sh:*)" \
				--max-turns "$turns" \
				"${flags[@]}" \
				--output-format stream-json --verbose 2>&1 | tee -a "$log"
			agent_status=${PIPESTATUS[0]}
			;;
		codex)
			# Everything through `-c` rather than through the flags that only
			# `codex exec` takes, because `codex exec resume` accepts a smaller
			# set and the two invocations must be configured the same way. Note
			# `--full-auto` is not among them at all: it does not exist in
			# codex-cli 0.150.1, so the branch that used it could never have run.
			#
			# `workspace-write` rather than the config's `danger-full-access`:
			# the repository and /tmp are writable and the network is open,
			# which is what a build needs and is the nearest thing codex has to
			# the deny list the claude branch above carries. Probed rather than
			# assumed -- /tmp and an outbound request both work under it.
			# `.git` among the writable roots, because workspace-write makes
			# it read-only and a run that cannot commit cannot follow the one
			# instruction the campaign depends on. Two builds were read as
			# "nothing built" for this: T161 filled 519 entries and T162 filled
			# 515, and both reported
			#
			#     fatal: Unable to create '.git/index.lock': Read-only file system
			#
			# which nobody saw, because the campaign only looked at whether a
			# generator had been committed. It was not disobedience.
			local flags=(--json --skip-git-repo-check
			             -m "$codex_model"
			             -c "model_reasoning_effort=$codex_effort"
			             -c "approval_policy=never"
			             -c "sandbox_mode=workspace-write"
			             -c "sandbox_workspace_write.network_access=true"
			             -c "sandbox_workspace_write.writable_roots=[\"$here/.git\"]")
			if [ "$mode" = "resume" ]; then
				codex exec resume "${flags[@]}" "$session" \
					"Continue where you left off." \
					</dev/null 2>&1 | tee -a "$log"
			else
				# stdin closed: with it open codex prints "Reading additional
				# input from stdin..." and waits for a prompt it already has.
				codex exec "${flags[@]}" "$briefing" \
					</dev/null 2>&1 | tee -a "$log"
			fi
			agent_status=${PIPESTATUS[0]}
			;;
		*)
			echo "unknown engine $engine" >&2; exit 2 ;;
	esac
}

# Whether the run died of something that trying again could survive: an API
# error, an expired token, an overload. Not a refusal and not running out of
# turns, where a second attempt spends the same money to be told the same
# thing.
worth_resuming() {
	tail -c 4000 "$log" 2>/dev/null | tr -d '\000' | grep -qE \
		'"api_error_status":[0-9]|OAuth access token has expired|overloaded_error|Internal server error|"type":"error"|stream disconnected|rate limit'
}

set +e
if [ -n "${NUMBERDB_RESUME:-}" ]; then
	run_agent resume
else
	run_agent start
fi
status=$agent_status
# Codex names its thread in the first event it prints, and that name is what
# resumes it -- here rather than in the ledger alone, because the retry below
# needs it too.
if [ "$engine" = "codex" ] && [ -z "$session" ]; then
	session=$(grep -ao '"thread_id":"[^"]*"' "$log" 2>/dev/null \
	          | head -1 | cut -d'"' -f4 || true)
fi
resumed=no
#Not for triage. Deciding whether a run is worth resuming is exactly the
#judgement this shell should not be making, and a triage run that fails
#should say so rather than quietly try again.
if [ "$status" -ne 0 ] && [ "$stage" != "triage" ] \
		&& [ "${NUMBERDB_NO_RETRY:-0}" != "1" ] && worth_resuming; then
	#The token first, because the commonest transient failure here is the
	#eight-hour boundary, and resuming into an expired token just fails again.
	if [ "$engine" = "claude" ]; then
		timeout 120 claude -p "Reply with exactly: ok" >/dev/null 2>&1 || true
	fi
	echo "=== $stage failed and looks resumable; continuing session $session once"
	run_agent resume
	status=$agent_status
	resumed=yes
fi
set -e

# A run that changed files and committed none of them looks, to everything
# downstream, like a run that did nothing. On 2026-09-06 a codex build wrote a
# 458-line generator, filled a 519-entry table and left both untracked; the
# campaign looks for a committed generator to decide a table was built, so it
# read that as an exhausted batch, went to propose a new one, and stopped on
# the dirty tree the build had left. Seven hours and $42.89, reported as
# nothing built.
#
# Said here, where the run's own status is reported, and left for a person:
# committing somebody else's work automatically is how a half-finished change
# becomes a commit nobody wrote.
unfinished=""
#`campaign.stop` is a person asking the campaign to stop between tables. It
#is never a run's work, and a run that happened to be going when somebody
#created it should not be called unfinished for it.
left=$(comm -13 <(printf '%s\n' "$tree_before") \
                <(git status --porcelain --untracked-files=normal | sort) \
       | grep -v 'agents/campaign\.stop$' || true)
if [ -n "$left" ]; then
	unfinished="left work uncommitted"
	echo "=== this run left changes it did not commit:"
	printf '%s\n' "$left" | sed 's/^/===   /'
	echo "===   the prompt asks a run to commit each change as it makes it."
	#And it did not finish, whatever it exited with. A run that declines --
	#"every proposal in that batch is already built, so I built nothing" --
	#leaves a clean tree; one that stopped in the middle leaves the work it
	#had done. Both exited 0 and the campaign could not tell them apart, so
	#it read the second as the first: on 2026-09-06 a codex build wrote a
	#519-entry table and was recorded as an exhausted batch, and on 2026-09-07
	#a claude build stopped with "waiting on the dry run" after 40 turns and
	#$10.05 and was recorded the same way.
	#
	#Non-zero sends it to triage, which is where the judgement belongs: a run
	#waiting on a computation it started is exactly what `resume` is for.
	if [ "$status" -eq 0 ]; then
		status=7
		echo "===   treating that as an unfinished run (exit 7)."
	fi
fi

# Which table this run was about, so the money can be attributed to one.
#
# The task names it for every stage that reads or repairs an existing table.
# A build does not know it in advance -- the number is allocated when the draft
# is created -- so it is read afterwards out of the generator the run
# committed, whose first docstring line names it by convention.
about=$(printf '%s' "${task:-}" | grep -oE '\bT[0-9]{2,4}\b' | head -1 || true)
if [ -z "$about" ]; then
	generator=$(git diff --name-only "$head_before"..HEAD -- generators/ \
	            2>/dev/null | grep -E 'generate\.py$' | head -1 || true)
	if [ -n "$generator" ] && [ -f "$generator" ]; then
		#The convention is the first line -- "... -- numberdb.org/T164" -- but
		#read the whole docstring, since a generator that says it lower down
		#still says it.
		about=$(head -40 "$generator" \
		        | grep -oE 'numberdb\.org/T[0-9]{2,4}' | head -1 \
		        | grep -oE 'T[0-9]{2,4}' || true)
	fi
fi

# What the run cost, in one line, appended to a ledger.
#
# Every run's result record carries `total_cost_usd`, and until this existed
# the only way to answer "what would this cost at scale" was to grep six
# transcripts by hand. The first five runs came to $56.94, which is the sort
# of number worth knowing before deciding to make eighty tables.
ledger="agents/runs/COSTS.tsv"
if [ ! -f "$ledger" ]; then
	python3 agents/ledger.py --header > "$ledger"
fi
# In a file of its own rather than a heredoc, because what it does is now
# arithmetic worth testing: two harnesses bill in different currencies -- one
# reports dollars, the other tokens -- and the ledger's job is to make the
# comparison possible at all. See agents/ledger.py and agents/model-rates.tsv.
python3 agents/ledger.py "$log" "$started" "$stage" "$engine" \
	"$prompt_version" "$session" "$resumed" "$codex_model" "$unfinished" \
	"$about" >> "$ledger" || true

#The ledger is tracked, so appending to it leaves the tree dirty -- and the
#next run refuses a dirty tree, by design. Committing the line here is what
#makes a sequence of runs possible: without it a campaign built exactly one
#table and stopped, and a sweep of critiques read exactly one, both of which
#looked like something else for an afternoon.
if [ -n "$(git status --porcelain -- "$ledger")" ]; then
	git add "$ledger"
	git commit -q -m "$stage run $started: $(tail -1 "$ledger" | awk -F'\t' '{printf "%s turns, $%s", $4, $5}')" -- "$ledger" || true
fi

#And into the database, so the overview shows what this run cost without
#anybody remembering a command. Never fatal: a ledger that did not reach the
#site is worth a warning, not a failed run.
agents/sync-costs.sh || true

echo "=== finished with status $status; transcript in $log"
tail -1 "$ledger" | awk -F'\t' '{printf "=== %s turns, $%s\n", $4, $5}'
exit "$status"
