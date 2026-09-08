"""Which table each past run was about.

    python3 scripts/one-off/attribute-past-runs-to-tables.py [apply]

The ledger grew a `table` column so money can be attributed to the table it
was spent on, and `run.sh` fills it from now on. The rows written before it
are recovered here from two sources, both of which are records rather than
guesses:

* the campaign logs, which name the table around each stage -- "reading T163
  as a reader would" sits between the build that made it and the critique that
  read it, and "acting on the critique of T163" before the repair;

* a list of the runs started by hand, outside any campaign, which no log
  records because there was no campaign to write one.

Not from the transcripts: neither harness echoes its briefing into the log, so
the first T-number in one is whatever the agent happened to look at first. An
earlier version of this script read T59 for three different builds that way.
"""
import io
import os
import re
import sys

LEDGER = 'agents/runs/COSTS.tsv'
APPLY = 'apply' in sys.argv[1:]

#: Runs I started by hand, which no campaign log records. Each is a fact
#: established when the run was made, not an inference.
BY_HAND = {
	'20260906T144234Z': 'T160',   # the critique the campaign skipped
	'20260906T160911Z': 'T160',   # and its repair
	'20260906T161625Z': 'T161',   # the codex build of the regulators table
	'20260907T014700Z': 'T162',   # the build that stopped mid dry run
	'20260907T061612Z': 'T162',   # its resume, refused on the weekly quota
	'20260907T070931Z': 'T161',   # codex reading its own table
	'20260907T080515Z': 'T162',   # codex finishing what the stalled build left
}

STAGE = re.compile(r'^=== (build|critique|repair|triage|ideas) run '
                   r'([0-9]{8}T[0-9]{6}Z)')
READING = re.compile(r'^=== reading (T[0-9]{2,4}) as a reader would')
ACTING = re.compile(r'^=== acting on the critique of (T[0-9]{2,4})')


def from_campaign_logs():
	"""stamp -> table, read out of what the campaign said it was doing."""
	found = {}
	import glob

	for path in sorted(glob.glob('agents/runs/campaign-*.log')
	                   + glob.glob('agents/runs/codex-*.log')):
		last_build = None
		pending = None
		try:
			lines = io.open(path, encoding='utf8', errors='replace')
		except OSError:
			continue
		for line in lines:
			line = line.rstrip('\n')
			stage = STAGE.match(line)
			if stage:
				kind, stamp = stage.groups()
				if kind == 'build':
					last_build = stamp
				elif pending:
					found[stamp] = pending
				continue
			reading = READING.match(line)
			if reading:
				#The build just before it made this table, and the critique
				#just after it reads the same one.
				pending = reading.group(1)
				if last_build:
					found[last_build] = pending
				continue
			acting = ACTING.match(line)
			if acting:
				pending = acting.group(1)
	return found


rows = [line.rstrip('\n').split('\t')
        for line in io.open(LEDGER, encoding='utf8')]
header, body = rows[0], rows[1:]
width = len(header)
index = {name: i for i, name in enumerate(header)}
if 'table' not in index:
	raise SystemExit('the ledger has no `table` column yet')

campaign = from_campaign_logs()
out = ['\t'.join(header)]
filled = blank = 0
for fields in body:
	if not any(fields):
		continue
	fields = (fields + [''] * width)[:width]
	stamp, stage = fields[0], fields[index['stage']]
	if not fields[index['table']]:
		tid = BY_HAND.get(stamp) or campaign.get(stamp, '')
		if tid:
			fields[index['table']] = tid
			filled += 1
			print('%s %-9s -> %s%s' % (stamp, stage, tid,
			                           '  (by hand)' if stamp in BY_HAND else ''))
		else:
			blank += 1
	out.append('\t'.join(fields))

print('\n%d attributed, %d left blank' % (filled, blank))
print('a stage about no table -- ideas, and a triage of a failed run -- stays blank')
if APPLY:
	io.open(LEDGER, 'w', encoding='utf8').write('\n'.join(out) + '\n')
	print('written')
else:
	print('dry run; pass "apply" to write it')
