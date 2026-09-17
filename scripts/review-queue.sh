#!/usr/bin/env bash
# What the corpus looks like, for the loop that reviews it.
#
#     scripts/review-queue.sh            # refresh agents/review-queue.tsv
#
# One line per table: number, entries, the size of its stored document, and
# its title. The reviewing stages need to know which tables are small for
# their subject and which have never been read, and a build machine has no
# database -- so this is taken from the server once and committed, rather than
# asked of the site three hundred times per campaign.
#
# Refresh it when the shape of the corpus has moved: after a campaign, or when
# the growth list stops making sense.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"

out="agents/review-queue.tsv"
{
	printf 'tid\tentries\tbytes\ttitle\n'
	agents/on-server.sh manage.py shell -c "
from numberdb_app.models import Table, TableData
for t in Table.objects.order_by('tid_int'):
    try:
        size = len(TableData.objects.get(table=t).full_yaml or '')
    except TableData.DoesNotExist:
        size = 0
    print('%s\t%d\t%d\t%s' % (t.tid, t.number_count, size, t.title.replace(chr(9), ' ')))
" 2>/dev/null | grep -P '^T\d+\t'
} > "$out.partial"

lines=$(grep -c '' "$out.partial" || true)
if [ "$lines" -lt 50 ]; then
	echo "only $lines lines; leaving $out alone" >&2
	rm -f "$out.partial"
	exit 1
fi
mv "$out.partial" "$out"
echo "$out: $((lines - 1)) tables"
