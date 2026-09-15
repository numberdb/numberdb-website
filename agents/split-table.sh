#!/usr/bin/env bash
# Split drafts that hold more than one named quantity.
#
#     agents/split-table.sh T232 T233          # these, if the audit flags them
#     agents/split-table.sh --why "the Glaisher-Kinkelin constant is one
#         table and the Bendersky family another" T227
#
# One run per table, because a split is a table's worth of judgement: what the
# two tables are called, which of them keeps the number, what the relation
# between them is, and whether to split at all -- the audit asks a question and
# three of its answers are good ones.
#
# With no `--why`, the audit's own finding is the task, and a table the audit
# does not flag is skipped rather than argued with. That is what makes this
# safe to point at a list.
#
# See `docs/design/where-ideas-live.md` for why the check exists and
# `agents/table-split/PROMPT.md` for what a split has to get right.

set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

why=""
if [ "${1:-}" = "--why" ]; then
	why="${2:-}"
	shift 2
fi
[ $# -gt 0 ] || { echo "usage: $0 [--why <reason>] <TID>..." >&2; exit 2; }

engine="${NUMBERDB_WRITER:-${NUMBERDB_AGENT:-claude}}"
host="${NUMBERDB_HOST:-https://numberdb.org}"
key_file="${NUMBERDB_KEY:-$HOME/.config/numberdb/zeta3-key}"
say() { printf '\n=== %s\n' "$*"; }
failed=""

# What the audit says about one table, as one line per finding.
findings() {
	local tid="$1"
	curl -sS --max-time 60 --noproxy '*' \
		-H "Authorization: Bearer $(cat "$key_file")" \
		"$host/api/table/$tid/audit" 2>/dev/null \
	| python3 -c 'import json,sys
try:
	body = json.load(sys.stdin)
except Exception:
	raise SystemExit(0)
for finding in body.get("findings", []):
	print(finding)'
}

for tid in "$@"; do
	task="$why"
	if [ -z "$task" ]; then
		#The finding, in the audit's own words, so the run is answering what
		#the reviewer will see rather than a paraphrase of it.
		task=$(findings "$tid" | grep 'sharing one title' | head -1 || true)
		if [ -z "$task" ]; then
			say "$tid: the audit does not say it holds more than one quantity; skipping"
			continue
		fi
	fi
	say "splitting $tid"
	#One table's run failing is not a reason to skip the rest: each split is
	#a separate table, a separate session and a separate judgement, and the
	#failures are named at the end rather than stopping the list.
	if ! NUMBERDB_AGENT="$engine" agents/run.sh split \
		"Split $tid, or say why it should stay as it is. The audit says: $task"
	then
		say "the split run for $tid failed; $tid is unchanged unless its report says otherwise"
		failed="$failed $tid"
	fi
done

if [ -n "$failed" ]; then
	say "these did not finish:$failed"
	exit 1
fi
