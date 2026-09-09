"""A table with no parameters writes its entries as a list, and an entry in
that list may be a mapping.

`to_nested` writes an entry as its bare value when the value is all it has,
and as `{number: ..., comment: ...}` when it has more. The number builder
handled the first and passed the second to `parse_integer`, which raised
TypeError -- reported by the write as "expected string or bytes-like object,
got 'dict'", an invalid document. Creating Lochs's constant with a comment on
its only entry failed that way, and the corpus's other parameterless tables
(T7 holds one value, T67 holds 442) never showed it because none of their
entries carries anything besides the value.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .editing import create_table
from .models import Number


class AParameterlessTableIndexesItsEntries(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('lochs', password='pw-123456')

	def make(self, entries):
		return create_table(
			{'Title': 'A constant',
			 'Definition': 'What this number is.',
			 'Parameters': '',
			 'Data properties': {'type': 'R'},
			 'Numbers': entries},
			author=self.user, via='orm')

	def values(self, table):
		return sorted(n.exact_text for n in Number.objects.filter(table=table))

	def test_a_bare_value_is_indexed(self):
		table = self.make(['3.14159'])
		self.assertEqual(self.values(table), ['3.14159'])

	def test_a_value_carrying_a_comment_is_indexed(self):
		table = self.make([{'number': '1.03064', 'comment': 'Lochs.'}])
		self.assertEqual(self.values(table), ['1.03064'])

	def test_several_entries_of_both_kinds_are_indexed(self):
		table = self.make(['2.71828',
		                   {'number': '1.03064', 'comment': 'Lochs.'}])
		self.assertEqual(self.values(table), ['1.03064', '2.71828'])

	def test_a_reference_without_digits_indexes_nothing_and_does_not_raise(self):
		table = self.make([{'equals': 'HREF{Pi}'}])
		self.assertEqual(self.values(table), [])
