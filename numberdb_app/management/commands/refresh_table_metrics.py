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


def sizes(table):
	"""How big this table's values are, in the unit its kind is measured in.

	Every kind is measured in characters, which is the one they share and the
	one a reader feels; numbers also in significant digits, p-adics in
	precision converted to decimal digits, polynomials in degree and terms.
	The median rather than the mean, because a single Igusa polynomial among a
	thousand short ones should not decide what the table looks like.
	"""
	from numberdb_app.measure import (p_adic_digits, polynomial_shape,
	                                  quartiles, significant_digits)

	chars, digits, degrees, terms = [], [], [], []

	for model in (Number, NumberComplex):
		for text in (model.objects.filter(table=table)
		             .values_list('exact_text', flat=True)):
			if not text:
				continue
			chars.append(len(text))
			found = significant_digits(text)
			if found:
				digits.append(found)

	for text in (NumberPAdic.objects.filter(table=table)
	             .values_list('number_string', flat=True)):
		if not text:
			continue
		chars.append(len(text))
		found = p_adic_digits(text)
		if found:
			digits.append(found)

	#Two texts per polynomial: the canonical one the index is built on, which
	#is what the shape is read from, and the one a reader sees, which is what
	#its length should be measured in. `1;1/1:|-1/1:x0^2` is not how long
	#`1 - x^2` looks.
	for canonical, shown in (Polynomial.objects.filter(table=table)
	                         .values_list('number_string', 'exact_text')):
		if not canonical:
			continue
		chars.append(len(shown or canonical))
		degree, count = polynomial_shape(canonical)
		if degree is not None:
			degrees.append(degree)
			terms.append(count)

	def median(values):
		found = quartiles(values)
		return found['median'] if found else None

	return {
		'value_chars_median': median(chars),
		'digits_median': median(digits),
		'degree_median': median(degrees),
		'terms_median': median(terms),
	}


def document_bytes(table):
	from numberdb_app.models import TableData

	try:
		document = TableData.objects.get(table=table)
	except TableData.DoesNotExist:
		return 0
	return len((document.full_yaml or '').encode('utf8'))


def refresh(table):
	spent = (TableCost.objects.filter(table=table)
	         .aggregate(total=Sum('cost_usd'))['total']) or Decimal('0')
	metrics, _ = TableMetrics.objects.update_or_create(
		table=table,
		defaults=dict({
			'entry_count': entry_count(table),
			'edit_count': table.revisions.count(),
			'data_type': declared_type(table),
			'agent_cost_usd': spent,
			'document_bytes': document_bytes(table),
		}, **sizes(table)))
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
				self.stdout.write(
					'%-6s %6d entries %4d edits %-5s %7d B  digits %-5s '
					'degree %-4s $%s'
					% (table.tid, metrics.entry_count, metrics.edit_count,
					   metrics.data_type, metrics.document_bytes,
					   metrics.digits_median, metrics.degree_median,
					   metrics.agent_cost_usd))
		self.stdout.write('refreshed %d tables' % (done,))
