"""One row per table in a search result.

Search answers "I have this number, what is it", and the answer wanted is the
list of contexts it appears in. A value occurring many times in one table --
`x` is a Chebyshev polynomial three times over, and a Legendre one, and a
Fibonacci one -- would otherwise fill the page with one family's rows and hide
every other answer.
"""

from django.test import TestCase

from .models import Number, Table


class ATableAppearsOnceHoweverOftenItHoldsTheValue(TestCase):

	def setUp(self):
		self.tables = []
		for i in range(3):
			table = Table.objects.create(
				tid='T80%d' % i, tid_int=800 + i, url='t80%d' % i,
				title='Table %d' % i, published=True)
			self.tables.append(table)

	def store(self, table, how_many, low=1.0, high=1.0):
		for _ in range(how_many):
			Number.objects.create(table=table, lower=low, upper=high,
			                      frac_lower=0.0, frac_upper=0.0,
			                      exact_relative_width=0.0, reviewed=True)

	def search(self, limit=10):
		from .search import one_per_table

		return one_per_table(Number.objects.filter(lower=1.0), limit)

	def test_a_table_with_many_matches_appears_once(self):
		self.store(self.tables[0], 6)
		rows = self.search()
		self.assertEqual(len(rows), 1)

	def test_the_count_is_carried_on_the_row(self):
		self.store(self.tables[0], 6)
		self.assertEqual(self.search()[0].occurrences_in_table, 6)

	def test_a_single_occurrence_counts_one(self):
		self.store(self.tables[0], 1)
		self.assertEqual(self.search()[0].occurrences_in_table, 1)

	def test_one_busy_table_no_longer_crowds_out_the_others(self):
		#The case that motivated this: without collapsing, the first table's
		#six rows fill a limit of three and the others never appear.
		self.store(self.tables[0], 6)
		self.store(self.tables[1], 1)
		self.store(self.tables[2], 1)
		rows = self.search(limit=3)
		self.assertEqual({row.table_id for row in rows},
		                 {t.pk for t in self.tables})

	def test_the_limit_counts_tables(self):
		for table in self.tables:
			self.store(table, 4)
		self.assertEqual(len(self.search(limit=2)), 2)

	def test_a_table_holding_nothing_matching_is_absent(self):
		self.store(self.tables[0], 2)
		self.store(self.tables[1], 1, low=9.0, high=9.0)
		rows = self.search()
		self.assertEqual([row.table_id for row in rows], [self.tables[0].pk])
