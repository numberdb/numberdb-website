"""A value that is stored, correct, displayed -- and answers no search.

The number builder skipped every entry carrying `equals`, so 101 values
across 16 tables were invisible to search by number while being perfectly
right. No check that looked at values could have found it, because the values
were not wrong. This one counts them instead.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Number, Table, TableRevision


class TheAuditNoticesEntriesMissingFromTheIndex(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('auditor')
		self.table = Table.objects.create(
			tid='T900', tid_int=900, url='t900', title='A table',
			published=True)
		TableRevision.objects.create(table=self.table, author=self.user,
		                             content='Title: A table\n')

	def complaints(self, tree):
		from .management.commands.audit_table import Command

		return list(Command()._indexed_as_many_as_written(self.table, tree))

	def index(self, how_many):
		for i in range(how_many):
			Number.objects.create(table=self.table, lower=float(i),
			                      upper=float(i), frac_lower=0.0,
			                      frac_upper=0.0, reviewed=True)

	def test_it_complains_when_digits_are_not_indexed(self):
		tree = {'Title': 'A table',
		        'Numbers': {'1': '2', '2': '3', '3': '5'}}
		found = self.complaints(tree)
		self.assertTrue(found)
		self.assertIn('cannot be found by their digits', found[0])

	def test_repeated_values_are_counted_once(self):
		#The Bernoulli numbers write 101 entries of which 49 are zero, and are
		#indexed correctly at 52. Counting entries called that broken.
		tree = {'Title': 'A table',
		        'Numbers': {'1': '0', '2': '0', '3': '0', '4': '7'}}
		self.index(2)
		self.assertEqual(self.complaints(tree), [])

	def test_a_type_the_search_cannot_hold_is_skipped(self):
		#T41's hyperreals are recorded and cited and were never findable.
		tree = {'Title': 'A table',
		        'Data properties': {'type': '*R'},
		        'Numbers': {'1': 'omega', '2': 'omega + 1'}}
		self.assertEqual(self.complaints(tree), [])

	def test_it_is_quiet_when_everything_is_indexed(self):
		tree = {'Title': 'A table', 'Numbers': {'1': '2', '2': '3'}}
		self.index(2)
		self.assertEqual(self.complaints(tree), [])

	def test_a_reference_without_digits_is_not_expected_in_the_index(self):
		#T94's s = 1 row points at a whole table and holds no value.
		tree = {'Title': 'A table',
		        'Numbers': {'1': {'equals': 'HREF{Pi}'}}}
		self.assertEqual(self.complaints(tree), [])

	def test_digits_beside_a_reference_are_expected(self):
		#The case that was broken: pi in T29, a hundred places and a pointer.
		tree = {'Title': 'A table',
		        'Numbers': {'1': {'number': '3.14159', 'equals': 'HREF{Pi}'}}}
		found = self.complaints(tree)
		self.assertTrue(found, 'an entry with digits must be expected to index')

	def test_more_rows_than_entries_is_not_a_complaint(self):
		#One written entry can hold a list of values.
		tree = {'Title': 'A table', 'Numbers': {'1': '2'}}
		self.index(4)
		self.assertEqual(self.complaints(tree), [])

	def test_a_table_with_no_numbers_says_nothing(self):
		self.assertEqual(self.complaints({'Title': 'A table'}), [])
