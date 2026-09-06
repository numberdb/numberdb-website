"""Every row says what it cost, including the ones written before it could.

    python3 scripts/one-off/price-the-ledger-in-usd.py [apply]

The ledger grew a cost column when the only engine reported one. Codex reports
tokens instead, so its first rows carried "3678199 tokens" in the result column
and nothing in the cost column, which is exactly the comparison the ledger
exists to make and could not.

This widens the file to the columns `agents/ledger.py` now writes and fills
what can be filled: the codex rows are priced from their logs where the logs
are still there, and the older claude rows keep the cost they already had --
the same quantity, list price in USD, which is why nothing needs recomputing.
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))), 'agents'))
sys.path.insert(0, 'agents')

import ledger

APPLY = 'apply' in sys.argv[1:]
PATH = 'agents/runs/COSTS.tsv'

rows = [line.rstrip('\n').split('\t')
        for line in io.open(PATH, encoding='utf8')]
header, body = rows[0], rows[1:]
width = len(ledger.COLUMNS)
out = ['\t'.join(ledger.COLUMNS)]
repriced = 0

for fields in body:
	if not any(fields):
		continue
	fields = (fields + [''] * width)[:width]
	started, stage, engine, turns, cost, result, log = fields[:7]
	if engine == 'codex' and not cost:
		path = os.path.join('agents/runs', log)
		found = ledger.codex_run(path, fields[7] or 'gpt-5.5') \
			if os.path.exists(path) else None
		if found and found['cost'] is not None:
			fields[3] = str(found['turns'])
			fields[4] = '%.4f' % found['cost']
			fields[5] = found['outcome']
			fields[11] = str(found['tokens_in'])
			fields[12] = str(found['tokens_cached'])
			fields[13] = str(found['tokens_out'])
			fields[14] = '%s=%.4f' % (found['model'], found['cost'])
			repriced += 1
			print('%s %-9s %s -> $%.4f' % (started, stage, engine, found['cost']))
		else:
			print('%s %-9s %s -> log is gone; left as it was'
			      % (started, stage, engine))
	out.append('\t'.join(fields))

print('\n%d rows, %d repriced, %d columns' % (len(out) - 1, repriced, width))
if APPLY:
	io.open(PATH, 'w', encoding='utf8').write('\n'.join(out) + '\n')
	print('written')
else:
	print('dry run; pass "apply" to write it')
