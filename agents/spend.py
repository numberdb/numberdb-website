"""What the campaign has spent, and on what.

    python3 agents/spend.py                # everything, by engine and by model
    python3 agents/spend.py --since 20260906   # from a run stamp onwards
    python3 agents/spend.py --by stage     # or engine, model, stage, day

Reads `agents/runs/COSTS.tsv`. Every row carries a cost in USD at list API
prices whichever harness produced it, which is the only figure comparable
across the two: see `agents/ledger.py`.
"""
import collections
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, 'runs', 'COSTS.tsv')


def rows(path=LEDGER):
	try:
		lines = io.open(path, encoding='utf8').read().splitlines()
	except OSError:
		return []
	if not lines:
		return []
	names = lines[0].split('\t')
	out = []
	for line in lines[1:]:
		fields = line.split('\t')
		if not any(fields):
			continue
		out.append(dict(zip(names, fields + [''] * (len(names) - len(fields)))))
	return out


def cost(row):
	try:
		return float(row.get('cost_usd') or 0)
	except ValueError:
		return 0.0


def summarise(found, key):
	totals = collections.Counter()
	runs = collections.Counter()
	for row in found:
		if key == 'day':
			name = (row.get('started') or '')[:8]
		elif key == 'model':
			#The per-model breakdown when there is one: a claude run bills a
			#little haiku beside its main model, and "which model" should mean
			#the model rather than the run.
			breakdown = row.get('cost_by_model') or ''
			if breakdown:
				for part in breakdown.split(';'):
					name, _, value = part.partition('=')
					try:
						totals[name] += float(value)
					except ValueError:
						pass
					runs[name] += 1
				continue
			name = row.get('model') or '(unknown)'
		else:
			name = row.get(key) or '(none)'
		totals[name] += cost(row)
		runs[name] += 1
	return totals, runs


def report(found, keys=('engine', 'model', 'stage')):
	total = sum(cost(row) for row in found)
	print('%d runs, $%.2f' % (len(found), total))
	for key in keys:
		totals, runs = summarise(found, key)
		if not totals:
			continue
		print('\nby %s' % key)
		for name, spent in totals.most_common():
			share = (100.0 * spent / total) if total else 0.0
			print('  %-28s $%9.2f  %5.1f%%  %3d runs'
			      % (name[:28], spent, share, runs[name]))


if __name__ == '__main__':
	arguments = sys.argv[1:]
	found = rows()
	if '--since' in arguments:
		since = arguments[arguments.index('--since') + 1]
		found = [row for row in found if (row.get('started') or '') >= since]
	keys = ('engine', 'model', 'stage')
	if '--by' in arguments:
		keys = (arguments[arguments.index('--by') + 1],)
	report(found, keys)
