#!/usr/bin/env bash
# Thin a directory of `numberdb-<stamp>.sql.gz` dumps to a sensible history.
#
#     scripts/thin-backups.sh                 # say what it would delete
#     scripts/thin-backups.sh --yes           # delete it
#     scripts/thin-backups.sh --yes /mnt/ext  # somewhere else
#
# Sixty daily copies of a database that changes by 20 MB a day is one day of
# safety stored sixty times. What anybody actually reaches for is yesterday,
# last week, or a particular month -- so this keeps the newest dump of each of
# the last 7 days, of each of the last 8 weeks, and of each of the last 12
# months, and drops the rest.
#
# Dry by default. Deleting backups is not a thing to do on a flag typed by
# accident, and the list it prints is short enough to read.
#
# This is for the old file-per-dump layout. Once `scripts/backup.sh` is storing
# restic snapshots, `restic forget` does the same job with the same policy and
# this script has nothing to look at.
set -euo pipefail

yes=no
if [ "${1:-}" = "--yes" ]; then
	yes=yes
	shift
fi
DEST="${1:-$HOME/numberdb-backups}"

# Below this, a file is not a backup however plausible its name. Two of the
# first fifty-one here were 20 and 980 bytes -- a run killed mid-write leaves a
# valid, empty gzip -- and the thinning kept one of them as a daily, which is
# the failure backups actually have: the copy you reach for is the broken one.
MIN_BYTES="${MIN_BYTES:-1000000}"

KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-8}"
KEEP_MONTHLY="${KEEP_MONTHLY:-12}"

[ -d "$DEST" ] || { echo "no such directory: $DEST" >&2; exit 2; }

python3 - "$DEST" "$yes" "$KEEP_DAILY" "$KEEP_WEEKLY" "$KEEP_MONTHLY" "$MIN_BYTES" <<'PY'
import datetime
import os
import re
import sys

directory, really, daily, weekly, monthly, floor = sys.argv[1:7]
daily, weekly, monthly, floor = int(daily), int(weekly), int(monthly), int(floor)

STAMP = re.compile(r'^numberdb-(\d{8})-(\d{6})\.sql\.gz$')
dumps = []
for name in os.listdir(directory):
    found = STAMP.match(name)
    if found:
        when = datetime.datetime.strptime(''.join(found.groups()), '%Y%m%d%H%M%S')
        path = os.path.join(directory, name)
        dumps.append((when, name, os.path.getsize(path)))
dumps.sort(reverse=True)

if not dumps:
    print('no dumps in %s' % directory)
    raise SystemExit(0)

#A file too small to be a dump is not one, and must not be kept as anything.
suspect = {name for _, name, size in dumps if size < floor}
dumps = [(when, name, size) for when, name, size in dumps if name not in suspect]
if not dumps:
    print('every file in %s is too small to be a dump; keeping all of them '
          'and looking no further' % directory)
    raise SystemExit(1)

#Newest first, and the first dump seen in each bucket is the one kept: the
#newest of that day, that week, that month. The same rule `restic forget` uses,
#so that the two agree about what a history looks like.
keep = {}
buckets = (('daily', daily, lambda d: d.strftime('%Y-%m-%d')),
           ('weekly', weekly, lambda d: '%s-W%s' % d.isocalendar()[:2]),
           ('monthly', monthly, lambda d: d.strftime('%Y-%m')))
for label, how_many, period_of in buckets:
    seen = []
    for when, name, size in dumps:
        period = period_of(when)
        if period in seen:
            continue
        seen.append(period)
        if len(seen) > how_many:
            break
        keep.setdefault(name, []).append(label)

#Whatever else happens, the newest dump stays: it is the one a restore starts
#from, and no policy is worth a directory whose newest file was pruned.
keep.setdefault(dumps[0][1], []).append('newest')

going = [(w, n, s) for w, n, s in dumps if n not in keep]
going += [(None, name, os.path.getsize(os.path.join(directory, name)))
          for name in sorted(suspect)]
freed = sum(size for _, _, size in going)
held = sum(size for w, n, size in dumps if n in keep)

for name in sorted(suspect, reverse=True):
    size = os.path.getsize(os.path.join(directory, name))
    print('  %-34s %6d B   NOT A DUMP' % (name, size))
for when, name, size in dumps:
    mark = ','.join(keep[name]) if name in keep else 'delete'
    print('  %-34s %6.1f MB  %s' % (name, size / 1048576.0, mark))

print('\nkeeping %d (%.1f GB), deleting %d (%.1f GB)'
      % (len(keep), held / 2**30, len(going), freed / 2**30))

if really != 'yes':
    print('\nnothing was deleted. Pass --yes to do it.')
    raise SystemExit(0)

for _, name, _ in going:
    os.remove(os.path.join(directory, name))
print('deleted %d dump(s), freeing %.1f GB' % (len(going), freed / 2**30))
PY
