#!/usr/bin/env bash
# Keep the agent runs' residue, and let the transcripts go.
#
#     scripts/agent-log.sh                    # sync the residue, prune old logs
#     scripts/agent-log.sh --dry-run          # say what it would do
#     KEEP_DAYS=30 scripts/agent-log.sh       # keep transcripts longer
#
# The runs produce two very different things. The transcripts are 82 MB and
# their value is extracted within hours -- triage reads one to decide what to
# do, the critique and the repair read the table rather than the log -- so
# they are pruned rather than kept. The residue is 668 KB and is the audit
# trail: what each run cost and which model answered, what triage decided,
# what the critiques found, which proposals not to attempt again.
#
# None of it is published. The source of truth is the tables themselves;
# reproducibility is the generate.py files, which are public; and a lesson is
# meant to end up distilled into a prompt or the skill, not kept raw. What is
# left here is worth surviving a disk, and nothing more.
#
# It goes to a private repository rather than into `scripts/backup.sh`,
# because that pulls the database *to this laptop* -- so putting the agent
# data beside it would leave one disk holding both copies, which is not a
# backup.

set -euo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

REPO="${NUMBERDB_AGENT_LOG_REPO:-git@github.com:numberdb/numberdb-agent-log.git}"
CHECKOUT="${NUMBERDB_AGENT_LOG:-$HOME/numberdb-agent-log}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DRY=""
[ "${1:-}" = "--dry-run" ] && DRY=1

say() { printf '\n=== %s\n' "$*"; }

if [ ! -d "$CHECKOUT/.git" ]; then
	say "cloning $REPO into $CHECKOUT"
	[ -n "$DRY" ] || git clone -q "$REPO" "$CHECKOUT"
	[ -n "$DRY" ] || printf '# Run residue from the numberdb table pipeline\n\nWritten by `scripts/agent-log.sh` in numberdb-website. Not code, and not\npublished: the tables are the source of truth and the generators are public.\nWhat is here is the audit trail -- what each run cost and which model\nanswered, what triage decided, what the critiques found.\n' > "$CHECKOUT/README.md"
fi

say "copying the residue"
for path in agents/critiques agents/lessons; do
	[ -d "$path" ] || continue
	echo "  $path"
	[ -n "$DRY" ] || { mkdir -p "$CHECKOUT/$path"; cp -a "$path/." "$CHECKOUT/$path/"; }
done
[ -n "$DRY" ] || mkdir -p "$CHECKOUT/agents/runs" "$CHECKOUT/agents/table-ideas"
for file in agents/runs/COSTS.tsv agents/table-ideas/SKIPPED.md; do
	[ -f "$file" ] || continue
	echo "  $file"
	[ -n "$DRY" ] || cp -a "$file" "$CHECKOUT/$file"
done
#The verdicts and the batches, which are one file per run and per batch.
for file in agents/runs/*-verdict agents/table-ideas/BATCH-*.md; do
	[ -e "$file" ] || continue
	[ -n "$DRY" ] || cp -a "$file" "$CHECKOUT/$file"
done
echo "  $(ls agents/runs/*-verdict 2>/dev/null | wc -l) verdict(s), $(ls agents/table-ideas/BATCH-*.md 2>/dev/null | wc -l) batch(es)"

#Never the transcripts, and never a key: the residue is prose and numbers,
#but a transcript is whatever the run printed, and one printed a key once.
say "checking nothing secret is going with it"
if [ -n "$(find "$CHECKOUT" -name '*.log' -not -path '*/.git/*' -print -quit 2>/dev/null)" ]; then
	echo "Refusing: a transcript reached the checkout." >&2
	exit 3
fi
if grep -rlIE '(Bearer [A-Za-z0-9_-]{30,}|NUMBERDB_API_KEY=[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)' \
		"$CHECKOUT" --exclude-dir=.git 2>/dev/null | head -1 | grep -q .; then
	echo "Refusing: something in the residue looks like a credential." >&2
	exit 3
fi
echo "  clean"

if [ -z "$DRY" ]; then
	say "committing"
	(
		cd "$CHECKOUT"
		git add -A
		if [ -n "$(git status --porcelain)" ]; then
			git commit -q -m "residue as of $(date -u +%Y-%m-%dT%H:%MZ)"
			git push -q origin HEAD 2>&1 | tail -2 || true
			echo "  pushed"
		else
			echo "  nothing changed"
		fi
	)
fi

say "pruning transcripts older than $KEEP_DAYS days"
if [ -n "$DRY" ]; then
	find agents/runs -maxdepth 1 -name '*.log' -mtime "+$KEEP_DAYS" -print | sed 's/^/  would remove /'
else
	removed=$(find agents/runs -maxdepth 1 -name '*.log' -mtime "+$KEEP_DAYS" -print -delete | wc -l)
	echo "  removed $removed"
fi
echo "  $(du -sh agents/runs 2>/dev/null | cut -f1) left in agents/runs"
