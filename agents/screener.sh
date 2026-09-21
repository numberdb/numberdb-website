#!/usr/bin/env bash
# Keep the proposal queue stocked. One process, and nothing else screens.
#
#     agents/screener.sh              # hold the queue at twelve proposals
#     agents/screener.sh 20           # or at twenty
#     touch agents/screener.stop      # finish the batch in flight and stop
#
# Whether the queue needs refilling is a question about the *shared* queue,
# and until now every builder answered it for itself: on 2026-09-21 the four
# workers between them ran ten screenings at $6 to $15 each, because each one
# that found the queue empty decided the remedy was to buy more proposals.
# One producer, a target depth, and the question is asked once.
#
# It builds nothing. A screening run costs about ten dollars and takes twenty
# minutes, so the loop is slow on purpose: it asks, and if the queue is deep
# enough it waits.
set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

#: How many unbuilt proposals to keep in front of the pool. Four builders take
#: about one an hour each and a screening yields four to seven, so twelve is
#: roughly three hours of work in hand -- enough that a failed screening is
#: not felt, and little enough that a proposal is still a claim about a corpus
#: it was screened against. A batch six weeks old is refused by `queue.py
#: stale` for exactly that reason.
target="${1:-${NUMBERDB_QUEUE_TARGET:-12}}"
every="${NUMBERDB_SCREEN_EVERY:-600}"

say() { printf '\n=== %s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

waiting_now() {
	python3 agents/queue.py open 2>/dev/null \
		| awk '/ waiting$/ {print $1}' | tail -1 || true
}

say "keeping the queue at $target proposals, looking every ${every}s"

while true; do
	if [ -e agents/screener.stop ] || [ -e agents/campaign.stop ]; then
		say "stop flag is there; stopping"
		exit 0
	fi

	waiting=$(waiting_now)
	if [ -z "$waiting" ]; then
		say "the queue could not be read; trying again shortly"
		sleep 60
		continue
	fi

	if [ "$waiting" -ge "$target" ]; then
		say "$waiting proposals waiting, which is enough"
		sleep "$every"
		continue
	fi

	say "$waiting proposals waiting, below $target; screening a family"
	#The screening job, not a campaign: it writes the batch, opens the issue
	#and archives the report, and a failure here is worth reporting and not
	#worth stopping for -- a quota refills, and the builders have work in hand.
	if NUMBERDB_SCREEN=1 agents/propose-batch.sh; then
		say "a family was opened"
	else
		say "the screening failed with status $?; waiting before trying again"
		sleep "$every"
	fi
	sleep 30
done
