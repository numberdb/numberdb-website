#!/usr/bin/env bash
# Keep N campaign workers running, and put them back when they stop.
#
#     agents/workers.sh 4            # keep four alive, checking every 5 minutes
#     touch agents/workers.stop      # let them finish and stay down
#
# A campaign is a loop that ends: at its item limit, at a failure it cannot
# judge, at a quota. Every one of those is a fine reason to stop *that* loop
# and a poor reason for the machine to go quiet -- which is what kept
# happening. On 2026-09-21 the four workers had been down to one for sixteen
# hours before anybody looked: two had finished their budgets, one had died
# on a stale claim and one on an unpushed commit, and each of those was
# already fixed. Nothing was watching.
#
# So this watches. It starts nothing itself beyond `campaign.sh`, decides
# nothing, and holds no state: whether a worker is running is a question the
# process table answers, and the answer is checked on a timer.
#
# Each worker gets its own worktree (scripts/campaign-worktree.sh) and its own
# name, which is what the ledger, the claims and the run records are keyed by.
# They share one critique directory, because "ask a table this question at
# most once" is a promise about the corpus, not about a worktree.
#
# **Editing this file does nothing until the supervisor itself is restarted.**
# Bash parses a function when it reads it, so a long-running `workers.sh` goes
# on starting workers from the `start()` and `start_screener()` it read at
# launch, however many times the file on disk has changed since. On 2026-09-22
# the screener was fixed, killed, and restarted by the supervisor -- with the
# old environment, because the supervisor was three hours older than the fix.
# The processes it starts are `setsid`, so it can be replaced without touching
# them:
#
#     kill <supervisor pid>                     # the workers keep running
#     setsid nohup agents/workers.sh 4 >> agents/runs/workers.log 2>&1 &
#
# Never `pkill -f workers.sh` and never `pkill -f campaign.sh`: the pattern
# matches every worker's loop as readily as the supervisor, and killing all
# four at once is a mistake this project has made more than once.
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

workers="${1:-4}"
every="${NUMBERDB_WORKERS_EVERY:-300}"
budget="${NUMBERDB_WORKER_BUDGET:-200}"

#: Shared between every worker. Outside the worktrees on purpose: four trees
#: meant four memories, and the same growth question was put to T293 twelve
#: times.
export NUMBERDB_CRITIQUES="${NUMBERDB_CRITIQUES:-$HOME/numberdb-critiques}"
mkdir -p "$NUMBERDB_CRITIQUES"

say() { printf '\n=== %s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

# Which engine reads and which proposes, when one of them may be gone.
#
# The writer is codex and the other two roles were claude, which is the right
# split while both work. A subscription ends on a date, though, and the pool
# should not need a person awake at that moment: `run.sh` exits 6 when it has
# spent every model its engine may use, and `campaign.sh` hands that stage to
# the other engine for the rest of the run. That covers claude going away
# *during* a campaign, and costs nothing -- the refusal happens in preflight,
# before a run spends anything.
#
# What it does not cover is claude being gone *before* a campaign starts: each
# restart would rediscover it, one refusal at a time, for ever. So the
# supervisor asks once, here, and tells the workers what it found. A wrong
# answer is cheap in both directions: if claude recovers, the next supervisor
# start picks it up again, and if it dies later the handover still fires.
#
# NUMBERDB_CRITIC or NUMBERDB_MINER set explicitly wins over the probe.
engine_for_reading() {
	if [ -n "${NUMBERDB_CRITIC:-}" ] || [ -n "${NUMBERDB_MINER:-}" ]; then
		return 0
	fi
	if ! command -v claude >/dev/null 2>&1; then
		say "no claude on PATH; codex reads and proposes"
		NUMBERDB_CRITIC=codex NUMBERDB_MINER=codex
		export NUMBERDB_CRITIC NUMBERDB_MINER
		return 0
	fi
	if timeout 120 claude -p 'Reply with exactly: ok' >/dev/null 2>&1; then
		say "claude answers; it reads and proposes, codex writes"
	else
		say "claude did not answer; codex reads and proposes for this run"
		NUMBERDB_CRITIC=codex NUMBERDB_MINER=codex
		export NUMBERDB_CRITIC NUMBERDB_MINER
	fi
}

tree_of() {                      # worker name -> its working tree
	if [ "$1" = w1 ]; then echo "$here"; else echo "$here/../numberdb-campaign-$1"; fi
}

running() {                      # is this worker's loop alive?
	#By the tree it is running in, which `ps` cannot show and /proc can: the
	#campaign's name lives in its environment, and its arguments are the same
	#for every worker. One worker, one worktree, so the working directory is
	#the identity.
	local tree
	tree=$(cd "$(tree_of "$1")" 2>/dev/null && pwd -P) || return 1
	local pid
	for pid in $(pgrep -f 'campaign\.sh' 2>/dev/null || true); do
		[ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null)" = "$tree" ] && return 0
	done
	return 1
}

start() {                        # one worker, in its own tree
	local name="$1" tree
	tree=$(tree_of "$name")
	[ -d "$tree" ] || { say "$name has no working tree at $tree"; return 1; }
	say "starting $name"
	(
		cd "$tree"
		[ -f "$HOME/.numberdb-gh" ] && . "$HOME/.numberdb-gh"
		export GH_TOKEN
		NUMBERDB_CAMPAIGN="$name" \
		NUMBERDB_WRITER="${NUMBERDB_WRITER:-codex}" \
		NUMBERDB_CRITIC="${NUMBERDB_CRITIC:-claude}" \
		NUMBERDB_MINER="${NUMBERDB_MINER:-claude}" \
		NUMBERDB_REMOTE="${NUMBERDB_REMOTE:-local}" \
		NUMBERDB_SAGE_IMAGE="${NUMBERDB_SAGE_IMAGE:-numberdb/builder:latest}" \
		NUMBERDB_SAGE_PYTHONPATH="${NUMBERDB_SAGE_PYTHONPATH:-}" \
		NUMBERDB_SAGE_MEMORY="${NUMBERDB_SAGE_MEMORY:-900m}" \
		NUMBERDB_KEY="${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}" \
		NUMBERDB_MACHINE="${NUMBERDB_MACHINE:-$(hostname -s)}" \
		NUMBERDB_CODEX_SANDBOX="${NUMBERDB_CODEX_SANDBOX:-danger-full-access}" \
		NUMBERDB_CRITIQUES="$NUMBERDB_CRITIQUES" \
		NUMBERDB_SCREEN=0 \
			setsid nohup agents/campaign.sh "$budget" \
				>> "agents/runs/campaign-$name.log" 2>&1 < /dev/null &
	)
}

#: The producer. One process screens; the builders only consume, which is the
#: whole of the arrangement: refilling a shared queue is a global decision and
#: four builders making it independently ran ten screenings in a day.
#:
#: It gets the *same* environment a builder gets, and not a shorter one. A
#: screening run computes -- it checks candidate values before proposing them
#: -- so it needs Sage exactly as a build does, and `start_screener` used to
#: leave the three NUMBERDB_SAGE_* settings out. `sage.sh` then fell back to
#: its default image, `numberdb/web:latest`, which does not exist on a build
#: machine: only `numberdb/builder:latest` does. Every screening refused with
#: "agents/sage.sh cannot run", the queue sat at zero, and the builders had
#: nothing to take.
screener_running() {
	local pid
	for pid in $(pgrep -f 'screener\.sh' 2>/dev/null || true); do
		[ -n "$pid" ] && return 0
	done
	return 1
}

start_screener() {
	say "starting the screener"
	(
		cd "$here"
		[ -f "$HOME/.numberdb-gh" ] && . "$HOME/.numberdb-gh"
		export GH_TOKEN
		NUMBERDB_CAMPAIGN="screener" \
		NUMBERDB_MINER="${NUMBERDB_MINER:-claude}" \
		NUMBERDB_REMOTE="${NUMBERDB_REMOTE:-local}" \
		NUMBERDB_KEY="${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}" \
		NUMBERDB_MACHINE="${NUMBERDB_MACHINE:-$(hostname -s)}" \
		NUMBERDB_CRITIQUES="$NUMBERDB_CRITIQUES" \
		NUMBERDB_CODEX_SANDBOX="${NUMBERDB_CODEX_SANDBOX:-danger-full-access}" \
		NUMBERDB_SAGE_IMAGE="${NUMBERDB_SAGE_IMAGE:-numberdb/builder:latest}" \
		NUMBERDB_SAGE_PYTHONPATH="${NUMBERDB_SAGE_PYTHONPATH:-}" \
		NUMBERDB_SAGE_MEMORY="${NUMBERDB_SAGE_MEMORY:-900m}" \
			setsid nohup agents/screener.sh \
				>> agents/runs/screener.log 2>&1 < /dev/null &
	)
}

engine_for_reading

say "keeping $workers builder(s) and one screener alive, looking every ${every}s"
say "writer ${NUMBERDB_WRITER:-codex}, critic ${NUMBERDB_CRITIC:-claude}, miner ${NUMBERDB_MINER:-claude}"
say "critiques shared in $NUMBERDB_CRITIQUES"

while true; do
	for flag in agents/workers.stop agents/campaign.stop; do
		if [ -e "$flag" ]; then
			say "$flag is there; leaving the workers alone and stopping"
			exit 0
		fi
	done

	if ! screener_running; then
		start_screener || true
		sleep 10
	fi

	for n in $(seq 1 "$workers"); do
		name="w$n"
		if ! running "$name"; then
			start "$name" || true
			#A moment between starts: four campaigns reading the queue in the
			#same second is four chances of the same proposal being offered
			#twice before any claim is written.
			sleep 20
		fi
	done
	sleep "$every"
done
