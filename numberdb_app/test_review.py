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
		                    base=base,
		via='orm').revision

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


class TheGateBites(TestCase):
	"""An unreviewed value must actually vanish from search by number.

	Asserted against the real search functions rather than by inspecting the
	flag, because a gate that is set but never consulted is the failure this
	is guarding against.
	"""

	def setUp(self):
		from sage.rings.all import RIF
		from numberdb_app.models import Number
		self.RIF = RIF
		self.table = Table.objects.create(tid='T902', tid_int=902,
		                                  title='Gate probe', url='Gate902')
		#A number precise enough to be identifiable, so the only thing that can
		#exclude it is the review flag.
		self.number = Number(sage_number=RIF('3.14159265358979323846'))
		self.number.table = self.table
		self.number.param = b'1'
		self.number.save()

	def _search(self):
		from numberdb_app.search import search_real_numbers
		from utils.utils import blur_real_interval
		#Deliberately the same digits as the stored value. A shorter query
		#produces an interval that does not reach it: blurring '3.14159' gives
		#a range ending below pi's stored lower bound, so it would find nothing
		#whatever the review flag said, and the test would pass for the wrong
		#reason in one direction and fail for the wrong reason in the other.
		query = blur_real_interval(self.RIF('3.1415926535897932'))
		return [n.pk for n in search_real_numbers(query, 20)]

	def test_a_reviewed_value_is_found(self):
		self.assertIn(self.number.pk, self._search())

	def test_an_unreviewed_value_is_not_found(self):
		from numberdb_app.models import Number
		Number.objects.filter(pk=self.number.pk).update(reviewed=False)
		self.assertNotIn(self.number.pk, self._search())

	def test_the_row_still_exists_and_is_still_shown(self):
		"""Excluded from search, not hidden: the page must still show it."""
		from numberdb_app.models import Number
		Number.objects.filter(pk=self.number.pk).update(reviewed=False)
		self.assertTrue(Number.objects.filter(pk=self.number.pk).exists())

	def test_sync_marks_only_what_changed(self):
		from numberdb_app.models import Number
		from .review import sync_review_flags
		#Parameters must be declared, or the builder treats the whole Numbers
		#mapping as a single entry and produces no rows at all. Committing
		#rebuilds the rows from this document, so the hand-made ones above are
		#replaced.
		def document(second_value):
			return {
				'Parameters': {'n': {'type': 'Z'}},
				'Numbers': {'1': '3.14159265358979323846',
				            '2': second_value},
			}

		first = commit_table(self.table, document('2.71828182845904523536'),
		                     author=User.objects.create(username='gate_probe'),
		via='orm')
		self.table.reviewed_at_revision = first.revision
		self.table.save(update_fields=['reviewed_at_revision'])
		self.table.refresh_from_db()
		self.assertEqual(Number.objects.filter(table=self.table).count(), 2)

		commit_table(self.table, document('1.41421356237309504880'),
		             base=first.revision,
		via='orm')
		self.table.refresh_from_db()

		rows = {n.param_str(): n for n in Number.objects.filter(table=self.table)}
		self.assertEqual(set(rows), {'1', '2'})
		self.assertTrue(rows['1'].reviewed)
		self.assertFalse(rows['2'].reviewed)
		#The untouched value is still findable; the changed one is not.
		found = self._search()
		self.assertIn(rows['1'].pk, found)
		self.assertNotIn(rows['2'].pk, found)


class ImportedContentIsNotAProposal(TestCase):
	"""What comes in from the data repository is the published corpus.

	Marked unreviewed it is held out of search by number, and since the import
	is the whole database that means every value: the site answers "no match"
	for numbers it plainly contains, with nothing logged and nothing looking
	wrong. This happened, and searching for 5.5 returned nothing across 45832
	values.
	"""

	def setUp(self):
		from .models import Table

		self.table = Table.objects.create(tid='T970', tid_int=970,
		                                  title='Import probe',
		                                  url='Import970')

	def test_a_table_whose_head_is_reviewed_lets_its_numbers_be_found(self):
		from .editing import commit_table
		from .models import Number
		from .review import sync_review_flags

		commit_table(self.table, {'Title': 'Import probe',
		                          'Parameters': {'n': {'type': 'R'}},
		                          'Numbers': {'1': '5.5'}}, author=None,
		via='orm')
		self.table.refresh_from_db()
		self.table.reviewed_at_revision = self.table.head_revision
		self.table.save(update_fields=['reviewed_at_revision'])
		sync_review_flags(self.table)
		self.assertEqual(
			Number.objects.filter(table=self.table, reviewed=False).count(), 0)

	def test_leaving_it_unreviewed_hides_every_value(self):
		"""The state the site was actually left in, asserted so it is visible."""
		from .editing import commit_table
		from .models import Number
		from .review import sync_review_flags

		commit_table(self.table, {'Title': 'Import probe',
		                          'Parameters': {'n': {'type': 'R'}},
		                          'Numbers': {'1': '5.5'}}, author=None,
		via='orm')
		self.table.refresh_from_db()
		sync_review_flags(self.table)
		self.assertGreater(
			Number.objects.filter(table=self.table, reviewed=False).count(), 0)


class TheSameEntryInTwoShapes(TestCase):
	"""The corpus holds entries in two shapes, and they mean the same thing.

	    Numbers: ['3.14159...']                                  # as imported
	    Numbers: [{'params': {}, 'number': '3.14159...'}]        # as rewritten

	Comparing those literally says the entry changed, so a metadata-only edit
	-- a rigour label, say -- marked every value in the table unreviewed and
	dropped it out of search by number. That happened to the whole corpus:
	71% of stored reals and every complex, p-adic and polynomial value.
	"""

	def test_the_two_shapes_are_not_a_change(self):
		from .review import changed_params

		before = {'Numbers': ['3.14159']}
		after = {'Numbers': [{'params': {}, 'number': '3.14159'}]}
		self.assertEqual(changed_params(before, after), set())

	def test_a_changed_value_in_the_other_shape_is_still_a_change(self):
		from .review import changed_params

		before = {'Numbers': ['3.14159']}
		after = {'Numbers': [{'params': {}, 'number': '3.14160'}]}
		self.assertEqual(changed_params(before, after), {''})

	def test_a_changed_comment_is_still_a_change(self):
		#Comparing only the number would let an altered proof or provenance
		#note through unreviewed, which is why the whole entry is compared.
		from .review import changed_params

		before = {'Numbers': [{'params': {}, 'number': '3.14159',
		                       'comment': 'from Archimedes'}]}
		after = {'Numbers': [{'params': {}, 'number': '3.14159',
		                      'comment': 'from a spreadsheet'}]}
		self.assertEqual(changed_params(before, after), {''})

	def test_an_added_entry_is_a_change(self):
		from .review import changed_params

		before = {'Numbers': {'1': '3.14'}}
		after = {'Numbers': {'1': '3.14', '2': '2.71'}}
		self.assertEqual(changed_params(before, after), {'2'})

	def test_a_removed_entry_is_a_change(self):
		from .review import changed_params

		before = {'Numbers': {'1': '3.14', '2': '2.71'}}
		after = {'Numbers': {'1': '3.14'}}
		self.assertEqual(changed_params(before, after), {'2'})

	def test_an_annotation_moved_by_normalisation_is_not_a_change(self):
		#`param-latex` sits on the entry in one shape and not the other, and
		#`url` and `both signs` move down onto entries from the node above.
		#2124, 1075 and 1075 entries respectively differed by exactly this.
		from .review import changed_params

		before = {'Numbers': {'1': {'param-latex': '$a$', 'number': '83521'}}}
		after = {'Numbers': [{'params': {'q': '1'}, 'number': '83521',
		                      'url': 'https://example.org/1'}]}
		self.assertEqual(changed_params(before, after), set())

	def test_a_changed_annotation_present_in_both_is_a_change(self):
		from .review import changed_params

		before = {'Numbers': {'1': {'number': '3.14', 'comment': 'measured'}}}
		after = {'Numbers': {'1': {'number': '3.14', 'comment': 'computed'}}}
		self.assertEqual(changed_params(before, after), {'1'})

	def test_a_changed_number_is_a_change_whatever_moved(self):
		from .review import changed_params

		before = {'Numbers': {'1': {'param-latex': '$a$', 'number': '83521'}}}
		after = {'Numbers': [{'params': {'q': '1'}, 'number': '83522'}]}
		self.assertEqual(changed_params(before, after), {'1'})

	def test_a_lone_value_wrapped_in_a_list_is_not_a_change(self):
		#The normalised shape writes `number: ['-188.5']` where the older one
		#has `number: '-188.5'`. T68 differed in 187 entries by only this.
		from .review import changed_params

		before = {'Numbers': {'-1316': '-1986121593'}}
		after = {'Numbers': [{'params': {'D': '-1316'},
		                      'number': ['-1986121593']}]}
		self.assertEqual(changed_params(before, after), set())

	def test_unparameterised_entries_do_not_collapse_onto_one_identity(self):
		#Every entry of a bare-list table carries `params: {}`, so keying by
		#the parameters gives them all the same identity and the last one
		#wins. T67's 442 values collapsed onto one.
		from .review import changed_params

		before = {'Numbers': ['0', '-6', '-9/5']}
		after = {'Numbers': [{'params': {}, 'number': '0'},
		                     {'params': {}, 'number': '-6'},
		                     {'params': {}, 'number': '-9/5'}]}
		self.assertEqual(changed_params(before, after), set())

	def test_a_changed_value_in_a_bare_list_is_still_a_change(self):
		from .review import changed_params

		before = {'Numbers': ['0', '-6', '-9/5']}
		after = {'Numbers': [{'params': {}, 'number': '0'},
		                     {'params': {}, 'number': '-7'},
		                     {'params': {}, 'number': '-9/5'}]}
		self.assertNotEqual(changed_params(before, after), set())

	def test_several_values_under_one_parameter_survive_normalisation(self):
		#T68: a discriminant with more than one j-invariant, stored as a bare
		#list before and as `number: [...]` after. 147 entries differed by
		#only this.
		from .review import changed_params

		before = {'Numbers': {'-10691': ['-188.5', '1.4562755']}}
		after = {'Numbers': [{'params': {'D': '-10691'},
		                      'number': ['-188.5', '1.4562755']}]}
		self.assertEqual(changed_params(before, after), set())

	def test_a_changed_value_among_several_is_still_a_change(self):
		from .review import changed_params

		before = {'Numbers': {'-10691': ['-188.5', '1.4562755']}}
		after = {'Numbers': [{'params': {'D': '-10691'},
		                      'number': ['-188.5', '1.4562766']}]}
		self.assertEqual(changed_params(before, after), {'-10691'})


class TheQueueIsCheapToLoad(TestCase):
	"""It used to diff every table's document against its last reviewed one.

	After a run that changed the metadata of every table in the corpus, that
	was 108 of 109 tables, each costing two YAML parses and a full entry
	comparison to prove that nothing had changed: forty seconds, and gunicorn
	killed the worker before the page arrived. The answer was already in the
	database, on an indexed column that `sync_review_flags` maintains.
	"""

	def setUp(self):
		from django.contrib.auth.models import Group, User

		from .editing import create_table
		from .permissions import BOARD_GROUP

		self.chair = User.objects.create_user('queue_chair', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.tables = [
			create_table({'Title': 'Queue probe %d' % n,
			              'Data properties': {'type': 'R'},
			              'Parameters': {'n': {'type': 'Z'}},
			              'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]},
			             author=self.chair,
		via='orm')
			for n in range(6)]
		self.client.force_login(self.chair)

	def test_it_asks_the_database_rather_than_the_documents(self):
		from django.test.utils import CaptureQueriesContext
		from django.db import connection

		with CaptureQueriesContext(connection) as queries:
			self.assertEqual(self.client.get('/review').status_code, 200)
		#A handful of aggregates and one table scan, not a query per table.
		self.assertLess(len(queries), 30, 'queries: %d' % len(queries))

	def test_a_table_with_unreviewed_entries_is_listed(self):
		from .editing import commit_table, tree_of

		table = self.tables[0]
		table.reviewed_at_revision = table.head_revision
		table.reviewed_by = self.chair
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])

		tree = dict(tree_of(table.head_revision))
		tree['Numbers'] = [{'params': {'n': '1'}, 'number': '3.15'}]
		commit_table(table, tree, author=self.chair, base=table.head_revision,
		             message='changed a digit',
		via='orm')

		body = self.client.get('/review').content.decode()
		self.assertIn(table.title, body)

	def test_a_table_whose_metadata_changed_is_not_listed(self):
		#The case that made the page slow: a rigour label moved and no digit
		#did. There is nothing for a reviewer to look at.
		from .editing import commit_table, tree_of

		table = self.tables[1]
		table.reviewed_at_revision = table.head_revision
		table.reviewed_by = self.chair
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])

		tree = dict(tree_of(table.head_revision))
		tree['Data properties'] = dict(tree['Data properties'],
		                               rigour='proven')
		commit_table(table, tree, author=self.chair, base=table.head_revision,
		             message='labelled',
		via='orm')

		body = self.client.get('/review').content.decode()
		self.assertNotIn(table.title, body)
