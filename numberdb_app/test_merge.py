"""Tests for the structural three-way merge.

Written harder than the code's size suggests, because the failure that matters
is silent: a merge that drops an entry produces a table that looks entirely
normal and is missing a number. Every deletion case below exists for that
reason.
"""

from django.test import SimpleTestCase

from .merge import MISSING, Conflict, merge


class DisjointEditsMerge(SimpleTestCase):
	"""The case that has to be free, because it is the common one."""

	def test_two_entries_edited_independently(self):
		base = {'Numbers': {'5': '1.234', '17': '5.678'}}
		mine = {'Numbers': {'5': '1.2345', '17': '5.678'}}
		theirs = {'Numbers': {'5': '1.234', '17': '5.6789'}}
		result = merge(base, mine, theirs)
		self.assertTrue(result.clean, result.conflicts)
		self.assertEqual(result.tree['Numbers'], {'5': '1.2345', '17': '5.6789'})

	def test_metadata_and_an_entry(self):
		base = {'Title': 'Pi', 'Numbers': {'1': '3.14'}}
		mine = {'Title': 'Pi (the circle constant)', 'Numbers': {'1': '3.14'}}
		theirs = {'Title': 'Pi', 'Numbers': {'1': '3.14159'}}
		result = merge(base, mine, theirs)
		self.assertTrue(result.clean, result.conflicts)
		self.assertEqual(result.tree['Title'], 'Pi (the circle constant)')
		self.assertEqual(result.tree['Numbers']['1'], '3.14159')

	def test_deeply_nested_entries_do_not_interfere(self):
		base = {'Numbers': {'2': {'1': {'0': '1/2', '2': '-1/6'}}}}
		mine = {'Numbers': {'2': {'1': {'0': '1/2', '2': '-1/6'}}}}
		theirs = {'Numbers': {'2': {'1': {'0': '1/2', '2': '-1/6'}}}}
		mine['Numbers']['2']['1']['0'] = '0.5'
		theirs['Numbers']['2']['1']['2'] = '-0.1666'
		result = merge(base, mine, theirs)
		self.assertTrue(result.clean, result.conflicts)
		self.assertEqual(result.tree['Numbers']['2']['1'],
		                 {'0': '0.5', '2': '-0.1666'})


class SameEditOnBothSides(SimpleTestCase):

	def test_identical_change_is_not_a_conflict(self):
		base = {'Title': 'Pi'}
		result = merge(base, {'Title': 'π'}, {'Title': 'π'})
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Title'], 'π')

	def test_identical_addition_is_not_a_conflict(self):
		base = {'Title': 'Pi'}
		added = {'Title': 'Pi', 'Keywords': 'circle'}
		result = merge(base, added, added)
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Keywords'], 'circle')


class RealConflicts(SimpleTestCase):

	def test_same_field_changed_differently(self):
		base = {'Title': 'Pi'}
		result = merge(base, {'Title': 'π'}, {'Title': 'Pi (circle)'})
		self.assertFalse(result.clean)
		self.assertEqual(len(result.conflicts), 1)
		c = result.conflicts[0]
		self.assertEqual(c.path, ('Title',))
		self.assertEqual((c.base, c.mine, c.theirs), ('Pi', 'π', 'Pi (circle)'))

	def test_same_entry_changed_differently(self):
		base = {'Numbers': {'5': '1.234'}}
		result = merge(base, {'Numbers': {'5': '1.2345'}},
		               {'Numbers': {'5': '1.2346'}})
		self.assertFalse(result.clean)
		self.assertEqual(result.conflicts[0].path, ('Numbers', '5'))

	def test_different_additions_of_the_same_key(self):
		base = {'Numbers': {}}
		result = merge(base, {'Numbers': {'9': 'a'}}, {'Numbers': {'9': 'b'}})
		self.assertFalse(result.clean)
		self.assertEqual(result.conflicts[0].path, ('Numbers', '9'))

	def test_the_merged_tree_stays_usable_during_a_conflict(self):
		"""A conflict must not produce a document that cannot be rendered."""
		base = {'Title': 'Pi', 'Numbers': {'1': '3.14'}}
		result = merge(base, {'Title': 'π', 'Numbers': {'1': '3.14'}},
		               {'Title': 'P', 'Numbers': {'1': '3.14159'}})
		self.assertFalse(result.clean)
		self.assertEqual(result.tree['Title'], 'π')        # mine, arbitrarily
		self.assertEqual(result.tree['Numbers']['1'], '3.14159')  # merged fine


class Deletions(SimpleTestCase):
	"""The dangerous direction. An entry lost silently looks like nothing."""

	def test_deleted_on_one_side_untouched_on_the_other(self):
		base = {'Numbers': {'5': '1.234', '17': '5.678'}}
		mine = {'Numbers': {'17': '5.678'}}
		theirs = {'Numbers': {'5': '1.234', '17': '5.678'}}
		result = merge(base, mine, theirs)
		self.assertTrue(result.clean, result.conflicts)
		self.assertEqual(result.tree['Numbers'], {'17': '5.678'})

	def test_deleted_on_one_side_edited_on_the_other_conflicts(self):
		base = {'Numbers': {'5': '1.234'}}
		mine = {'Numbers': {}}
		theirs = {'Numbers': {'5': '1.9999'}}
		result = merge(base, mine, theirs)
		self.assertFalse(result.clean)
		c = result.conflicts[0]
		self.assertEqual(c.kind, 'delete')
		self.assertEqual(c.path, ('Numbers', '5'))
		#Kept, not dropped: a conflict a person can see beats a quiet loss.
		self.assertEqual(result.tree['Numbers'], {'5': '1.9999'})

	def test_deleted_on_both_sides(self):
		base = {'Numbers': {'5': '1.234', '17': '5.678'}}
		gone = {'Numbers': {'17': '5.678'}}
		result = merge(base, gone, gone)
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Numbers'], {'17': '5.678'})

	def test_a_whole_section_deleted_while_edited(self):
		base = {'Comments': {'a': 'text'}, 'Title': 'T'}
		mine = {'Title': 'T'}
		theirs = {'Comments': {'a': 'edited'}, 'Title': 'T'}
		result = merge(base, mine, theirs)
		self.assertFalse(result.clean)
		self.assertEqual(result.conflicts[0].kind, 'delete')
		self.assertIn('Comments', result.tree)


class NoneIsAValue(SimpleTestCase):
	"""`Comments:` with nothing under it is None, and that is a real state."""

	def test_empty_section_is_not_the_same_as_a_missing_one(self):
		base = {'Comments': None}
		mine = {'Comments': None}
		theirs = {}
		result = merge(base, mine, theirs)
		self.assertTrue(result.clean, result.conflicts)
		self.assertNotIn('Comments', result.tree)

	def test_filling_in_an_empty_section(self):
		base = {'Comments': None}
		result = merge(base, {'Comments': 'now says something'},
		               {'Comments': None})
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Comments'], 'now says something')


class Lists(SimpleTestCase):
	"""Compared whole, because their order carries meaning."""

	def test_one_side_changes_a_list(self):
		base = {'Tags': ['pi', 'transcendental']}
		result = merge(base, {'Tags': ['pi', 'transcendental', 'irrational']},
		               {'Tags': ['pi', 'transcendental']})
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Tags'],
		                 ['pi', 'transcendental', 'irrational'])

	def test_both_sides_change_a_list_differently(self):
		base = {'Tags': ['pi']}
		result = merge(base, {'Tags': ['pi', 'circle']},
		               {'Tags': ['pi', 'irrational']})
		self.assertFalse(result.clean)
		self.assertEqual(result.conflicts[0].path, ('Tags',))

	def test_reordering_a_list_is_a_change(self):
		base = {'Tags': ['a', 'b']}
		result = merge(base, {'Tags': ['b', 'a']}, {'Tags': ['a', 'b']})
		self.assertTrue(result.clean)
		self.assertEqual(result.tree['Tags'], ['b', 'a'])


class KeyOrder(SimpleTestCase):
	"""A table's keys are in a deliberate order; a merge must not sort them."""

	def test_base_order_is_preserved(self):
		base = {'ID': 'T1', 'Title': 'x', 'Definition': 'd', 'Numbers': {}}
		mine = dict(base, Title='y')
		theirs = dict(base, Definition='e')
		result = merge(base, mine, theirs)
		self.assertEqual(list(result.tree),
		                 ['ID', 'Title', 'Definition', 'Numbers'])

	def test_added_keys_come_after_existing_ones(self):
		base = {'ID': 'T1', 'Title': 'x'}
		mine = {'ID': 'T1', 'Title': 'x', 'Keywords': 'k'}
		theirs = {'ID': 'T1', 'Title': 'x', 'Tags': ['t']}
		result = merge(base, mine, theirs)
		self.assertEqual(list(result.tree)[:2], ['ID', 'Title'])
		self.assertEqual(set(list(result.tree)[2:]), {'Keywords', 'Tags'})


class Isolation(SimpleTestCase):
	"""The inputs belong to the caller and must come back untouched."""

	def test_inputs_are_not_mutated(self):
		base = {'Numbers': {'1': 'a'}}
		mine = {'Numbers': {'1': 'b'}}
		theirs = {'Numbers': {'1': 'a', '2': 'c'}}
		before = (repr(base), repr(mine), repr(theirs))
		result = merge(base, mine, theirs)
		self.assertEqual((repr(base), repr(mine), repr(theirs)), before)
		result.tree['Numbers']['1'] = 'mutated'
		self.assertEqual(mine['Numbers']['1'], 'b')


class TypeChanges(SimpleTestCase):

	def test_scalar_becoming_a_mapping_on_one_side(self):
		base = {'Numbers': {'1': '3.14'}}
		mine = {'Numbers': {'1': {'number': '3.14', 'comment': 'c'}}}
		theirs = {'Numbers': {'1': '3.14159'}}
		result = merge(base, mine, theirs)
		self.assertFalse(result.clean)
		self.assertEqual(result.conflicts[0].kind, 'type')
