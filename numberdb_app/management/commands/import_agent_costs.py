"""Bring the agent runs' ledger into the database.

    manage.py import_agent_costs agents/runs/COSTS.tsv
    manage.py import_agent_costs COSTS.tsv --dry-run

The ledger lives beside the runs, on whoever's machine ran them, and prices
every run in API-equivalent USD whichever harness produced it (see
`agents/ledger.py`). This reads it and keeps one row per table, model and
role, so that "what did this table cost", "what has that model cost us" and
"what does critiquing cost against building" are all answerable.

Rows are replaced, not added to, so importing the same ledger twice leaves the
same numbers. A run with no table -- an ideas run proposing a batch, a triage
deciding what to do about a failure -- belongs to no table and is skipped;
its cost is in the ledger and in `agents/spend.py`, which is the right place
for work that is not about one table.
"""
import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from numberdb_app.models import Table, TableCost


def parse_breakdown(row):
	"""(model, cost) pairs for one run.

	`cost_by_model` is what the ledger writes when it knows the split -- a
	claude run bills a little haiku beside its main model, and "which model"
	should mean the model. Falls back to the run's headline model and cost.
	"""
	pairs = []
	for part in (row.get('cost_by_model') or '').split(';'):
		name, _, value = part.partition('=')
		if not name.strip() or not value.strip():
			continue
		try:
			pairs.append((name.strip(), Decimal(value.strip())))
		except InvalidOperation:
			continue
	if pairs:
		return pairs
	model = (row.get('model') or '').strip()
	try:
		cost = Decimal((row.get('cost_usd') or '0').strip() or '0')
	except InvalidOperation:
		return []
	return [(model or '(unknown)', cost)] if cost else []


class Command(BaseCommand):
	help = "Import per-table agent costs from an agents/runs/COSTS.tsv."

	def add_arguments(self, parser):
		parser.add_argument('ledger')
		parser.add_argument('--dry-run', action='store_true')

	def handle(self, *args, **options):
		try:
			handle = open(options['ledger'], encoding='utf8', newline='')
		except OSError as problem:
			raise CommandError(str(problem))

		known = {table.tid: table for table in Table.objects.all()}
		#(table, model, role) -> [cost, runs]
		totals = defaultdict(lambda: [Decimal('0'), 0])
		engines = {}
		skipped = 0
		with handle:
			for row in csv.DictReader(handle, delimiter='\t'):
				tid = (row.get('table') or '').strip().upper()
				table = known.get(tid)
				if table is None:
					skipped += 1
					continue
				role = (row.get('stage') or '').strip()[:16]
				for model, cost in parse_breakdown(row):
					key = (table.pk, model[:64], role)
					totals[key][0] += cost
					totals[key][1] += 1
					engines[key] = (row.get('engine') or '').strip()[:16]

		if options['dry_run']:
			for (table_pk, model, role), (cost, runs) in sorted(totals.items()):
				self.stdout.write('%-6s %-10s %-26s $%8.4f  %d run(s)'
				                  % (Table.objects.get(pk=table_pk).tid, role,
				                     model, cost, runs))
			self.stdout.write('%d rows would be written, %d runs named no table'
			                  % (len(totals), skipped))
			return

		#Replaced rather than added to, so importing twice is not paying twice.
		TableCost.objects.filter(
			table__pk__in={pk for pk, _, _ in totals}).delete()
		TableCost.objects.bulk_create([
			TableCost(table_id=table_pk, model=model, role=role,
			          engine=engines.get((table_pk, model, role), ''),
			          cost_usd=cost, runs=runs)
			for (table_pk, model, role), (cost, runs) in totals.items()])

		from numberdb_app.management.commands.refresh_table_metrics import refresh

		for table_pk in {pk for pk, _, _ in totals}:
			refresh(Table.objects.get(pk=table_pk))
		self.stdout.write('%d cost rows over %d tables; %d runs named no table'
		                  % (len(totals), len({pk for pk, _, _ in totals}),
		                     skipped))
