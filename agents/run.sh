#!/usr/bin/env bash
# Run one stage of the table pipeline in a fresh, unattended agent session.
#
#     agents/run.sh ideas                 # stage one: propose a batch
#     agents/run.sh build "proposal 1 of agents/table-ideas/BATCH-2026-08-30.md"
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
	*) echo "usage: $0 {ideas|build} [task]" >&2; exit 2 ;;
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

export NUMBERDB_AGENT_RUN=1
export NUMBERDB_ASSISTED_BY="assisted by $engine (numberdb agent run $started)"
export NUMBERDB_KEY_FILE="$key_file"

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

**Do not deploy.** \`scripts/ship.sh\` will refuse anyway.

**Commit** each change as you make it, with a message saying what you learned
rather than what you touched. Do not push.

**When something you met is not in the skill**, append it to
\`agents/lessons/PROPOSALS.md\` in the format given there. Do not edit the
skill itself: a person promotes a lesson, together with a test.

## Your task

${task:-Follow the prompt above.}
BRIEF
)

echo "=== $stage run $started, engine $engine" | tee "$log"

case "$engine" in
	claude)
		claude -p "$briefing" \
			--permission-mode acceptEdits \
			--max-turns "$turns" \
			--output-format stream-json --verbose 2>&1 | tee -a "$log"
		;;
	codex)
		codex exec --full-auto "$briefing" 2>&1 | tee -a "$log"
		;;
	*)
		echo "unknown engine $engine" >&2; exit 2 ;;
esac

status=${PIPESTATUS[0]}
echo "=== finished with status $status; transcript in $log"
exit "$status"
