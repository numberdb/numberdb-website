"""Recompute the overview's derived numbers.

    manage.py refresh_table_metrics            # every table
    manage.py refresh_table_metrics T163 T162  # named ones

Nothing here is a source of truth. Entries are counted from the stored rows,
because that is what search answers from; edits are revisions, because every
edit is one however it arrived; the type is what the document declares. If a
row disagrees with its table, the table is right and this is stale.

The work is in `numberdb_app/metrics.py`, which runs after every write as
well, so a table reaches the overview when it is created rather than when
somebody remembers this command. Run it after the columns change or the cost
ledger is imported.
"""
from django.core.management.base import BaseCommand

from numberdb_app.metrics import refresh
from numberdb_app.models import Table


class Command(BaseCommand):
	help = "Recompute TableMetrics from the tables themselves."

	def add_arguments(self, parser):
		parser.add_argument('tids', nargs='*',
		                    help='table numbers; default every table')

	def handle(self, *args, **options):
		tables = Table.objects.all()
		if options['tids']:
			wanted = [t.upper() for t in options['tids']]
			tables = tables.filter(tid__in=wanted)
		done = 0
		for table in tables.order_by('tid_int'):
			metrics = refresh(table)
			done += 1
			if options['verbosity'] > 1:
				self.stdout.write(
					'%-6s %6d entries %4d edits %-5s %7d B  digits %-5s '
					'degree %-4s $%s'
					% (table.tid, metrics.entry_count, metrics.edit_count,
					   metrics.data_type, metrics.document_bytes,
					   metrics.digits_median, metrics.degree_median,
					   metrics.agent_cost_usd))
		self.stdout.write('refreshed %d tables' % (done,))
