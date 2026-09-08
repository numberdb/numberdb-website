"""Recompute the overview's derived numbers.

    manage.py refresh_table_metrics            # every table
    manage.py refresh_table_metrics T163 T162  # named ones

Nothing here is a source of truth. Entries are counted from the stored rows,
because that is what search answers from; edits are revisions, because every
edit is one however it arrived; the type is what the document declares. If a
row disagrees with its table, the table is right and this is stale.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from numberdb_app.models import (Number, NumberComplex, NumberPAdic,
                                 Polynomial, Table, TableCost, TableMetrics)


def entry_count(table):
	"""Stored rows of every kind."""
	return sum(model.objects.filter(table=table).count()
	           for model in (Number, NumberComplex, NumberPAdic, Polynomial))


def declared_type(table):
	from numberdb_app.models import TableData

	try:
		document = TableData.objects.get(table=table).json
	except TableData.DoesNotExist:
		return ''
	properties = (document or {}).get('Data properties')
	if not isinstance(properties, dict):
		return ''
	return str(properties.get('type') or '')[:32]


def refresh(table):
	spent = (TableCost.objects.filter(table=table)
	         .aggregate(total=Sum('cost_usd'))['total']) or Decimal('0')
	metrics, _ = TableMetrics.objects.update_or_create(
		table=table,
		defaults={
			'entry_count': entry_count(table),
			'edit_count': table.revisions.count(),
			'data_type': declared_type(table),
			'agent_cost_usd': spent,
		})
	return metrics


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
				self.stdout.write('%-6s %6d entries %4d edits %-5s $%s'
				                  % (table.tid, metrics.entry_count,
				                     metrics.edit_count, metrics.data_type,
				                     metrics.agent_cost_usd))
		self.stdout.write('refreshed %d tables' % (done,))
