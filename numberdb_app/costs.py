"""What an agent run cost, from the ledger into the database.

The ledger is a TSV a run appends to on whatever machine it ran on. It reaches
here two ways and must mean the same thing both times: `manage.py
import_agent_costs` reads a file, and `POST /api/costs` takes the same text
over the wire from a build machine that has no ssh to this server and should
not need one.

Aggregated by (table, model, role) and *replaced* rather than added to, so
sending the same ledger twice is not paying twice -- which matters more here
than it did for a file, because a build machine will send the whole ledger
after every run rather than once at the end.
"""

import csv
import io
from collections import defaultdict
from decimal import Decimal, InvalidOperation


def parse_breakdown(row):
	"""The per-model costs of one run.

	`cost_by_model` when the run recorded one -- a run that fell back to a
	second model spent money on both, and a single total would put all of it
	on whichever model happened to be named in `model`. Otherwise the total
	against the one model it names.
	"""
	breakdown = (row.get('cost_by_model') or '').strip()
	if breakdown:
		found = []
		#Semicolons, because that is what `agents/ledger.py` writes -- and
		#commas too, because this read only commas and the ledger only wrote
		#semicolons, so every run that used a second model had that model's
		#cost silently folded into the first one's name and then dropped as
		#unparseable. The whole point of the column is the fallback run that
		#spent money on two models.
		import re as _re

		for part in _re.split(r'[;,]', breakdown):
			name, _, amount = part.partition('=')
			name = name.strip()
			try:
				cost = Decimal(amount.strip() or '0')
			except InvalidOperation:
				continue
			if name:
				found.append((name, cost))
		if found:
			return found

	try:
		cost = Decimal((row.get('cost_usd') or '0').strip() or '0')
	except InvalidOperation:
		return []
	model = (row.get('model') or '').strip()
	return [(model, cost)] if model else []


def read_attributions(text):
	"""Runs that named no table, attributed by hand.

	Two columns, run stamp and table, tabs between, `#` for a comment.
	"""
	found = {}
	for line in io.StringIO(text or ''):
		line = line.strip()
		if not line or line.startswith('#'):
			continue
		stamp, _, tid = line.partition('\t')
		stamp, tid = stamp.strip(), tid.strip().upper()
		if stamp and tid:
			found[stamp] = tid
	return found


def ingest(ledger_text, attribution_text='', dry_run=False, machine=''):
	"""Put a ledger's costs on the tables they belong to.

	Returns a summary dict. Never raises on a row it cannot use: a ledger is
	written by many runs over weeks and one malformed line should not stop the
	other four hundred.
	"""
	from .models import Table, TableCost

	known = {table.tid: table for table in Table.objects.all()}
	#Only consulted for a row that names no table: the ledger is what a run
	#said about itself and wins where it spoke.
	attributed = read_attributions(attribution_text)

	#Keyed by the table when there is one and by None when there is not. Work
	#that produced no table is still work somebody paid for: a third of the
	#builds here failed or found nothing, and a table that took three attempts
	#cost what all three attempts cost. Counting those and dropping them, as
	#this did, makes every total 22% short.
	totals = defaultdict(lambda: [Decimal('0'), 0])
	engines = {}
	unattached = rescued = 0

	rows = list(csv.DictReader(io.StringIO(ledger_text or ''), delimiter='\t'))

	#The run itself, not only what it spent. A screening run, a triage run and
	#the third of builds that fail or decline write no revision at all, so
	#before this they existed only as a line in a file on whichever machine
	#happened to run them. Costs are aggregated below; a run is a thing.
	if not dry_run:
		from .provenance import runs_from_ledger
		runs_from_ledger(rows, machine=machine)

	for row in rows:
		tid = (row.get('table') or '').strip().upper()
		if not tid:
			tid = attributed.get((row.get('started') or '').strip(), '')
			if tid:
				rescued += 1
		table = known.get(tid)
		if table is None:
			unattached += 1
		role = (row.get('stage') or '').strip()[:16]
		campaign = (row.get('campaign') or '').strip()[:64]
		batch = (row.get('batch') or '').strip()[:64]
		for model, cost in parse_breakdown(row):
			key = (table.pk if table else None, model[:64], role,
			       campaign, batch)
			totals[key][0] += cost
			totals[key][1] += 1
			engines[key] = (row.get('engine') or '').strip()[:16]

	touched = {key[0] for key in totals if key[0] is not None}
	summary = {
		'rows': len(totals),
		'tables': len(touched),
		#Still reported, because a large number here is worth seeing -- but no
		#longer thrown away.
		'unattributed': unattached,
		'unattributed_usd': float(sum(
			cost for key, (cost, _) in totals.items() if key[0] is None)),
		'rescued': rescued,
		'applied': not dry_run,
	}
	if dry_run:
		return summary

	#Replaced rather than added to, so importing twice is not paying twice.
	#The table-less rows are replaced by campaign, for the same reason: a
	#machine sends its whole ledger after every run.
	campaigns = {key[3] for key in totals if key[0] is None}
	TableCost.objects.filter(table__pk__in=touched).delete()
	TableCost.objects.filter(table__isnull=True,
	                         campaign__in=campaigns).delete()
	TableCost.objects.bulk_create([
		TableCost(table_id=table_pk, model=model, role=role,
		          campaign=campaign, batch=batch,
		          engine=engines.get(key, ''),
		          cost_usd=cost, runs=runs)
		for key, (cost, runs) in totals.items()
		for (table_pk, model, role, campaign, batch) in [key]])

	#The overview reads TableMetrics, and the cost it shows is summed from the
	#rows just written.
	from .metrics import refresh

	for table_pk in touched:
		refresh(Table.objects.get(pk=table_pk))
	return summary
