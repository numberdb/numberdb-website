"""Tests for entries as flat records.

The property that matters is not that the conversion is pretty but that no
citation changes meaning. An entry's identity is its parameter values, and
every anchor, every `?entry=`, every cross-reference from another table and
every search result is built from it. A flattening that quietly renumbered
them would break nothing visibly and point thousands of links at the wrong
numbers.
"""

import yaml
from django.test import SimpleTestCase, TestCase

from . import flatten


class Grouping(SimpleTestCase):

	def test_one_group_per_parameter_by_default(self):
		tree = {'Parameters': {'n': {}, 'k': {}}}
		self.assertEqual(flatten.parameter_groups(tree), [['n'], ['k']])

	def test_a_display_property_can_group_two_into_one_level(self):
		"""Eleven tables do this, and it decides how the entries parse."""
		tree = {'Parameters': {'N': {}, 'c4': {}, 'c6': {}},
		        'Display properties': {'group parameters': [['N'], ['c4', 'c6']]}}
		self.assertEqual(flatten.parameter_groups(tree), [['N'], ['c4', 'c6']])

	def test_a_grouped_key_is_split_and_stripped(self):
		"""`112, -856` is stored with a space and cited without one."""
		self.assertEqual(flatten.split_key('112, -856', ['c4', 'c6']),
		                 {'c4': '112', 'c6': '-856'})

	def test_a_key_of_the_wrong_shape_is_not_guessed_at(self):
		"""Shifting values into the next parameter would be silent and wrong."""
		self.assertEqual(flatten.split_key('5', ['c4', 'c6']),
		                 {'c4': '5', 'c6': None})


class Converting(SimpleTestCase):

	def test_a_plain_nested_table_becomes_records(self):
		tree = {'Parameters': {'n': {}},
		        'Numbers': {'1': '3.14', '2': '2.71'}}
		self.assertEqual(flatten.to_records(tree), [
			{'params': {'n': '1'}, 'number': '3.14'},
			{'params': {'n': '2'}, 'number': '2.71'},
		])

	def test_annotations_travel_with_the_entry(self):
		tree = {'Parameters': {'n': {}},
		        'Numbers': {'1': {'number': '3.14', 'comment': 'about pi',
		                          'proof': 'CITE{x}'}}}
		self.assertEqual(flatten.to_records(tree), [
			{'params': {'n': '1'}, 'number': '3.14',
			 'comment': 'about pi', 'proof': 'CITE{x}'},
		])

	def test_a_numbers_container_yields_its_contents(self):
		"""The shape that collapsed T33, T34 and T36 to two entries each."""
		tree = {'Parameters': {'expression': {}, 'n': {}},
		        'Numbers': {'a_n': {'param-latex': '$a_n$',
		                            'numbers': {'0': '1.1', '1': '2.2'}}}}
		records = flatten.to_records(tree)
		self.assertEqual(len(records), 2)
		self.assertEqual(records[0]['params'], {'expression': 'a_n', 'n': '0'})
		#Metadata covering the whole group is repeated onto each record.
		self.assertEqual(records[0]['param-latex'], '$a_n$')

	def test_grouped_parameters_are_named_where_they_are_used(self):
		tree = {'Parameters': {'N': {}, 'c4': {}, 'c6': {}},
		        'Display properties': {'group parameters': [['N'], ['c4', 'c6']]},
		        'Numbers': {'389': {'112, -856': '1.518'}}}
		self.assertEqual(flatten.to_records(tree), [
			{'params': {'N': '389', 'c4': '112', 'c6': '-856'},
			 'number': '1.518'},
		])

	def test_a_table_with_no_parameters_is_a_list_of_values(self):
		tree = {'Numbers': ['0', '-6', '-9/5']}
		self.assertEqual([r['number'] for r in flatten.to_records(tree)],
		                 ['0', '-6', '-9/5'])

	def test_several_numbers_under_one_parameter_stay_together(self):
		tree = {'Parameters': {'n': {}},
		        'Numbers': {'1': ['3.14', '3.15']}}
		self.assertEqual(flatten.to_records(tree),
		                 [{'params': {'n': '1'}, 'number': ['3.14', '3.15']}])


class Identities(SimpleTestCase):

	GROUPS = [['N'], ['c4', 'c6']]
	RECORD = {'params': {'N': '389', 'c4': '112', 'c6': '-856'}}

	def test_the_positional_identity_is_what_the_anchors_already_use(self):
		self.assertEqual(flatten.identity_of(self.RECORD, self.GROUPS),
		                 '389,112,-856')

	def test_the_named_identity_says_which_value_is_which(self):
		self.assertEqual(flatten.named_identity_of(self.RECORD, self.GROUPS),
		                 'N=389,c4=112,c6=-856')

	def test_the_named_identity_survives_a_reordering_the_positional_does_not(self):
		"""The failure worth preventing: a citation that resolves and lies."""
		swapped = [['c4', 'c6'], ['N']]
		self.assertNotEqual(flatten.identity_of(self.RECORD, self.GROUPS),
		                    flatten.identity_of(self.RECORD, swapped))
		self.assertEqual(
			sorted(flatten.named_identity_of(self.RECORD, self.GROUPS).split(',')),
			sorted(flatten.named_identity_of(self.RECORD, swapped).split(',')))


class RoundTrip(SimpleTestCase):

	def convert(self, tree):
		groups = flatten.parameter_groups(tree)
		records = flatten.to_records(tree)
		rebuilt = dict(tree)
		rebuilt.pop('Data', None)
		rebuilt['Numbers'] = flatten.to_nested(records, groups)
		return records, flatten.to_records(rebuilt)

	def test_a_nested_table_survives_the_round_trip(self):
		tree = {'Parameters': {'n': {}, 'k': {}},
		        'Numbers': {'1': {'2': '3.14'}, '5': {'6': '2.71'}}}
		first, second = self.convert(tree)
		self.assertEqual(first, second)

	def test_a_parameterless_table_keeps_every_value(self):
		"""T67 holds 442 of these; an early return kept only the first."""
		tree = {'Numbers': [str(i) for i in range(50)]}
		first, second = self.convert(tree)
		self.assertEqual(len(first), 50)
		self.assertEqual(first, second)

	def test_grouped_parameters_survive(self):
		tree = {'Parameters': {'N': {}, 'c4': {}, 'c6': {}},
		        'Display properties': {'group parameters': [['N'], ['c4', 'c6']]},
		        'Numbers': {'389': {'112, -856': '1.518', '0, 1': '2.0'}}}
		first, second = self.convert(tree)
		self.assertEqual(first, second)


class TheWholeCorpus(TestCase):
	"""Against the real tables, which is the only test that settles this.

	Skipped on a bare database; it earns its keep against a populated one.
	"""

	def loaded(self):
		from .models import TableData

		out = []
		for td in TableData.objects.select_related('table').all()[:200]:
			tree = yaml.load(td.full_yaml, Loader=yaml.BaseLoader) or {}
			if flatten.entries_block(tree) is not None:
				out.append((td.table.tid, tree))
		return out

	def test_every_identity_survives_flattening(self):
		"""Not one citation may change what it points at."""
		from .review import flatten_entries

		tables = self.loaded()
		if not tables:
			self.skipTest('no tables loaded')
		for tid, tree in tables:
			groups = flatten.parameter_groups(tree)
			before = set(flatten_entries(flatten.entries_block(tree)))
			after = {flatten.identity_of(r, groups)
			         for r in flatten.to_records(tree)}
			self.assertEqual(before, after, tid)

	def test_every_table_round_trips(self):
		tables = self.loaded()
		if not tables:
			self.skipTest('no tables loaded')
		for tid, tree in tables:
			groups = flatten.parameter_groups(tree)
			first = flatten.to_records(tree)
			rebuilt = dict(tree)
			rebuilt.pop('Data', None)
			rebuilt['Numbers'] = flatten.to_nested(first, groups)
			self.assertEqual(first, flatten.to_records(rebuilt), tid)


class ParameterLabelsLiveOnTheParameter(SimpleTestCase):
	"""`v: b` is the identity and `$b$` is how it is shown.

	Both are needed and they are different things. What is not needed is a copy
	of the display on every record: it is a property of the value, so it is
	stated once on the parameter. All 5178 records in the corpus that carried
	one had it determined entirely by a single parameter value.
	"""

	def test_the_identity_is_the_plain_value(self):
		tree = {'Parameters': {'q': {'type': 'R'},
		                       'v': {'type': 'Symbolic',
		                             'values': {'b': '$b$'}}},
		        'Numbers': [{'params': {'q': '1.62', 'v': 'b'},
		                     'number': '6436341'}]}
		groups = flatten.parameter_groups(tree)
		record = flatten.to_records(tree)[0]
		self.assertEqual(flatten.identity_of(record, groups), '1.62,b')
		self.assertEqual(flatten.named_identity_of(record, groups),
		                 'q=1.62,v=b')


class RecordsGoInAndOutUnchanged(SimpleTestCase):
	"""Documents are stored flat, so a caller is as likely to hand over records
	as nested entries. Walked as though the list were a value, a whole table
	became one entry."""

	def test_a_flat_block_is_returned_as_records(self):
		tree = {'Parameters': {'n': {}},
		        'Numbers': [{'params': {'n': '1'}, 'number': '3.14'},
		                    {'params': {'n': '2'}, 'number': '2.71'}]}
		self.assertEqual(flatten.to_records(tree), tree['Numbers'])

	def test_converting_twice_changes_nothing(self):
		tree = {'Parameters': {'n': {}}, 'Numbers': {'1': '3.14'}}
		once = flatten.to_records(tree)
		twice = flatten.to_records({'Parameters': {'n': {}}, 'Numbers': once})
		self.assertEqual(once, twice)
