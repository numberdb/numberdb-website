"""Tests for the unreviewed set.

The property that matters is precision: editing one entry must mark that entry
and no other. A gate that marked the whole table on any edit would make review
so coarse that nobody would do it, and would quietly remove thousands of good
values from search by number.
"""

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from .editing import commit_table
from .models import Table
from .review import (ALL_UNREVIEWED, changed_params, flatten_entries,
                     unreviewed_params)


class Flattening(SimpleTestCase):

	def test_one_parameter(self):
		self.assertEqual(set(flatten_entries({'5': 'a', '17': 'b'})),
		                 {'5', '17'})

	def test_several_parameters_join_with_commas(self):
		"""Matching Number.param_str(), so rows can be looked up directly."""
		flat = flatten_entries({'3/4': {'0': 'x'}})
		self.assertEqual(set(flat), {'3/4,0'})

	def test_three_levels(self):
		flat = flatten_entries({'2': {'1': {'0': '1/2', '2': '-1/6'}}})
		self.assertEqual(set(flat), {'2,1,0', '2,1,2'})

	def test_an_entry_with_extra_information_is_not_a_parameter_level(self):
		"""A dict carrying `number` is the entry, not another parameter."""
		flat = flatten_entries({'5': {'number': '3.14', 'comment': 'c'}})
		self.assertEqual(set(flat), {'5'})
		self.assertEqual(flat['5'], {'number': '3.14', 'comment': 'c'})

	def test_a_cross_reference_is_an_entry(self):
		flat = flatten_entries({'1': {'equals': 'HREF{Bernoulli_numbers}'}})
		self.assertEqual(set(flat), {'1'})

	def test_no_entries(self):
		self.assertEqual(flatten_entries(None), {})
		self.assertEqual(flatten_entries({}), {})


class ShapesFoundInTheRealCorpus(SimpleTestCase):
	"""Both of these were wrong until the identities were checked against the
	rows they have to match. Neither would have failed loudly."""

	def test_a_numbers_container_is_not_the_end_of_the_walk(self):
		"""T33's shape. Taking this as terminal collapsed 500 entries to 2."""
		flat = flatten_entries({
			'a_n': {'param-latex': '$a_n$',
			        'numbers': {'0': '1', '1': '2', '2': '3'}},
			'a_n/n!': {'param-latex': '$a_n/n!$',
			           'numbers': {'0': '1', '1': '0.5'}},
		})
		self.assertEqual(set(flat),
		                 {'a_n,0', 'a_n,1', 'a_n,2', 'a_n/n!,0', 'a_n/n!,1'})

	def test_a_grouped_parameter_key_loses_its_spaces(self):
		"""T69's shape: the YAML says `64, 296`, the row says `64,296`."""
		flat = flatten_entries({'101': {'64, 296': 'x'}})
		self.assertEqual(set(flat), {'101,64,296'})

	def test_a_comment_beside_a_number_stays_part_of_the_entry(self):
		"""Otherwise a comment-only edit passes review unnoticed."""
		before = {'Numbers': {'5': {'number': '3.14', 'comment': 'old'}}}
		after = {'Numbers': {'5': {'number': '3.14', 'comment': 'new'}}}
		self.assertEqual(changed_params(before, after), {'5'})


class ChangedParams(SimpleTestCase):

	def test_editing_one_entry_marks_only_that_entry(self):
		before = {'Numbers': {'5': 'a', '17': 'b', '42': 'c'}}
		after = {'Numbers': {'5': 'CHANGED', '17': 'b', '42': 'c'}}
		self.assertEqual(changed_params(before, after), {'5'})

	def test_adding_an_entry(self):
		self.assertEqual(
			changed_params({'Numbers': {'5': 'a'}},
			               {'Numbers': {'5': 'a', '9': 'new'}}),
			{'9'})

	def test_removing_an_entry_counts_as_a_change(self):
		"""Search must not keep returning a value somebody deleted."""
		self.assertEqual(
			changed_params({'Numbers': {'5': 'a', '9': 'b'}},
			               {'Numbers': {'5': 'a'}}),
			{'9'})

	def test_changing_a_comment_marks_the_entry(self):
		before = {'Numbers': {'5': {'number': '3.14', 'comment': 'old'}}}
		after = {'Numbers': {'5': {'number': '3.14', 'comment': 'new'}}}
		self.assertEqual(changed_params(before, after), {'5'})

	def test_editing_metadata_marks_no_entry(self):
		"""A better title says nothing about whether the digits are right."""
		before = {'Title': 'Pi', 'Numbers': {'5': 'a'}}
		after = {'Title': 'Pi (circle constant)', 'Numbers': {'5': 'a'}}
		self.assertEqual(changed_params(before, after), set())

	def test_the_old_Data_spelling_still_diffs(self):
		"""Revisions committed before the schema normalisation say Data."""
		self.assertEqual(
			changed_params({'Data': {'1': 'x'}}, {'Data': {'1': 'y'}}),
			{'1'})

	def test_nothing_changed(self):
		tree = {'Numbers': {'5': 'a', '17': 'b'}}
		self.assertEqual(changed_params(tree, dict(tree)), set())


class UnreviewedParams(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T901', tid_int=901,
		                                  title='Probe', url='Probe901')
		self.user = User.objects.create(username='reviewer_probe')

	def commit(self, tree, base=None):
		return commit_table(self.table, tree, author=self.user,
		                    base=base).revision

	def test_a_table_never_edited_here_is_treated_as_reviewed(self):
		"""The imported corpus arrived through pull requests."""
		self.assertEqual(unreviewed_params(self.table), set())

	def test_a_table_with_history_and_no_review_is_wholly_unreviewed(self):
		self.commit({'Numbers': {'1': 'a'}})
		self.table.refresh_from_db()
		self.assertIs(unreviewed_params(self.table), ALL_UNREVIEWED)

	def test_review_current_means_nothing_outstanding(self):
		r = self.commit({'Numbers': {'1': 'a'}})
		self.table.reviewed_at_revision = r
		self.table.save(update_fields=['reviewed_at_revision'])
		self.table.refresh_from_db()
		self.assertEqual(unreviewed_params(self.table), set())

	def test_only_what_changed_since_review_is_outstanding(self):
		first = self.commit({'Numbers': {'1': 'a', '2': 'b', '3': 'c'}})
		self.table.reviewed_at_revision = first
		self.table.save(update_fields=['reviewed_at_revision'])
		self.commit({'Numbers': {'1': 'a', '2': 'CHANGED', '3': 'c'}},
		            base=first)
		self.table.refresh_from_db()
		self.assertEqual(unreviewed_params(self.table), {'2'})

	def test_two_edits_since_review_accumulate(self):
		first = self.commit({'Numbers': {'1': 'a', '2': 'b'}})
		self.table.reviewed_at_revision = first
		self.table.save(update_fields=['reviewed_at_revision'])
		second = self.commit({'Numbers': {'1': 'X', '2': 'b'}}, base=first)
		self.commit({'Numbers': {'1': 'X', '2': 'Y'}}, base=second)
		self.table.refresh_from_db()
		self.assertEqual(unreviewed_params(self.table), {'1', '2'})

	def test_an_edit_that_was_reverted_is_not_outstanding(self):
		"""Review compares against head, not against every step taken."""
		first = self.commit({'Numbers': {'1': 'a'}})
		self.table.reviewed_at_revision = first
		self.table.save(update_fields=['reviewed_at_revision'])
		second = self.commit({'Numbers': {'1': 'wrong'}}, base=first)
		self.commit({'Numbers': {'1': 'a'}}, base=second)
		self.table.refresh_from_db()
		self.assertEqual(unreviewed_params(self.table), set())
