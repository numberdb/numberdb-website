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

if [ "$engine" = "claude" ]; then
	floor="${NUMBERDB_TOKEN_FLOOR:-90}"
	left=$(token_minutes_left)
	if [ "$left" != "unknown" ] && [ "$left" -lt "$floor" ] 2>/dev/null; then
		echo "=== $left minutes of token left, under the $floor-minute floor; refreshing"
		timeout 120 claude -p "Reply with exactly: ok" >/dev/null 2>&1 || true
		left=$(token_minutes_left)
		if [ "$left" != "unknown" ] && [ "$left" -lt "$floor" ] 2>/dev/null; then
			echo "Refusing: $left minutes of token left and the refresh did not" >&2
			echo "take. Re-authenticate (claude auth login), or lower" >&2
			echo "NUMBERDB_TOKEN_FLOOR if this run is a short one." >&2
			exit 6
		fi
		echo "=== refreshed; $left minutes now"
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
session="$(python3 -c 'import uuid; print(uuid.uuid4())')"
if [ -n "${NUMBERDB_RESUME:-}" ]; then
	session="$NUMBERDB_RESUME"
	start_flags=(--resume "$session")
	echo "=== resuming session $session"
else
	start_flags=(--session-id "$session")
fi

agent_status=0

run_agent() {
	case "$engine" in
		claude)
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
				"$@" \
				--output-format stream-json --verbose 2>&1 | tee -a "$log"
			agent_status=${PIPESTATUS[0]}
			;;
		codex)
			codex exec --full-auto "$briefing" 2>&1 | tee -a "$log"
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
		'"api_error_status":[0-9]|OAuth access token has expired|overloaded_error|Internal server error'
}

set +e
run_agent "${start_flags[@]}"
status=$agent_status
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
	run_agent --resume "$session"
	status=$agent_status
	resumed=yes
fi
set -e

# What the run cost, in one line, appended to a ledger.
#
# Every run's result record carries `total_cost_usd`, and until this existed
# the only way to answer "what would this cost at scale" was to grep six
# transcripts by hand. The first five runs came to $56.94, which is the sort
# of number worth knowing before deciding to make eighty tables.
ledger="agents/runs/COSTS.tsv"
if [ ! -f "$ledger" ]; then
	printf 'started\tstage\tengine\tturns\tcost_usd\tresult\tlog\tmodel\tprompt\tsession\tresumed\n' > "$ledger"
fi
python3 - "$log" "$started" "$stage" "$engine" "$prompt_version" "$session" "$resumed" >> "$ledger" <<'LEDGER' || true
import json, os, sys
path, started, stage, engine, prompt, session, resumed = sys.argv[1:8]
last = None
#Which model actually answered. Known only now: the CLI chooses it, and the
#first assistant message in the transcript says which. This is the durable
#record of it -- the ledger is tracked and the transcripts are not.
model = ''

try:
	for line in open(path, errors='replace'):
		line = line.strip()
		if line.startswith('{'):
			try:
				record = json.loads(line)
			except Exception:
				continue
			if not model:
				named = (record.get('message') or {}).get('model')
				if isinstance(named, str) and named:
					model = named
			if record.get('type') == 'result':
				last = record
except OSError:
	pass
if last is None:
	print('%s\t%s\t%s\t\t\tno result record\t%s\t%s\t%s\t%s\t%s'
	      % (started, stage, engine, os.path.basename(path), model, prompt,
	         session, resumed))
else:
	#`subtype` says "success" even when the run ended on an API error: the
	#401 that stopped the campaign on 2026-09-03 was recorded as a success by
	#every field except this one.
	outcome = last.get('subtype', '')
	if last.get('is_error'):
		outcome = 'error %s' % (last.get('api_error_status')
		                        or last.get('subtype') or '',)
	print('%s\t%s\t%s\t%s\t%.2f\t%s\t%s\t%s\t%s\t%s\t%s'
	      % (started, stage, engine, last.get('num_turns', ''),
	         last.get('total_cost_usd', 0) or 0, outcome.strip(),
	         os.path.basename(path), model, prompt, session, resumed))
LEDGER

#The ledger is tracked, so appending to it leaves the tree dirty -- and the
#next run refuses a dirty tree, by design. Committing the line here is what
#makes a sequence of runs possible: without it a campaign built exactly one
#table and stopped, and a sweep of critiques read exactly one, both of which
#looked like something else for an afternoon.
if [ -n "$(git status --porcelain -- "$ledger")" ]; then
	git add "$ledger"
	git commit -q -m "$stage run $started: $(tail -1 "$ledger" | awk -F'\t' '{printf "%s turns, $%s", $4, $5}')" -- "$ledger" || true
fi

echo "=== finished with status $status; transcript in $log"
tail -1 "$ledger" | awk -F'\t' '{printf "=== %s turns, $%s\n", $4, $5}'
exit "$status"
