"""Tests for the revision history, and for going back to an earlier version.

Restoring is the thing that makes publish-immediately defensible, so the
assertions here are mostly about what a restore does *not* do: it does not
erase the revisions in between, it does not skip the review gate, and it does
not let a table be rewritten from a version somebody else has already moved
past without that being recorded.
"""

from django.contrib.auth.models import Group, User
from django.test import TestCase

from .editing import commit_table, restore_revision, tree_of
from .models import Table, TableRevision
from .permissions import BOARD_GROUP


class RestoreBase(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T920', tid_int=920,
		                                  title='History probe',
		                                  url='History920')
		self.alice = User.objects.create_user('alice_h', password='pw-123456')
		self.chair = User.objects.create_user('chair_h', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])

	def commit(self, tree, who=None, base=None, message=''):
		return commit_table(self.table, tree, author=who or self.alice,
		                    message=message, base=base).revision

	def head_tree(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)


class Restoring(RestoreBase):

	def setUp(self):
		super().setUp()
		self.good = self.commit({'Title': 'History probe',
		                         'Numbers': {'1': '3.14159'}},
		                        message='the right value')
		self.bad = self.commit({'Title': 'History probe',
		                        'Numbers': {'1': '2.71828'}},
		                       base=self.good, message='a mistake')

	def test_the_content_comes_back(self):
		restore_revision(self.table, self.good, author=self.alice)
		self.assertEqual(self.head_tree()['Numbers'], {'1': '3.14159'})

	def test_the_mistake_is_still_in_the_history(self):
		"""The whole argument for committing forward rather than rewinding."""
		restore_revision(self.table, self.good, author=self.alice)
		messages = [r.message for r in self.table.revisions.all()]
		self.assertIn('a mistake', messages)
		self.assertEqual(TableRevision.objects.filter(table=self.table).count(), 3)

	def test_the_restore_is_a_child_of_what_it_replaced(self):
		out = restore_revision(self.table, self.good, author=self.alice)
		self.assertEqual(out.revision.parent_id, self.bad.pk)

	def test_a_restore_can_itself_be_undone(self):
		restore_revision(self.table, self.good, author=self.alice)
		restore_revision(self.table, self.bad, author=self.alice)
		self.assertEqual(self.head_tree()['Numbers'], {'1': '2.71828'})

	def test_restoring_the_current_version_changes_nothing(self):
		before = TableRevision.objects.filter(table=self.table).count()
		out = restore_revision(self.table, self.bad, author=self.alice)
		self.assertTrue(out.unchanged)
		self.assertEqual(TableRevision.objects.filter(table=self.table).count(),
		                 before)

	def test_a_revision_of_another_table_is_refused(self):
		other = Table.objects.create(tid='T921', tid_int=921, title='Other',
		                             url='Other921')
		with self.assertRaises(ValueError):
			restore_revision(other, self.good, author=self.alice)


class RestoringPastAParameterChange(RestoreBase):
	"""The one place the parameter freeze has to give way.

	An ordinary edit may not change the parameter list, because that reassigns
	every entry's identity at once. But if an edit somehow did, refusing to
	restore would strand the table in exactly the state the freeze exists to
	prevent, so a restore is allowed through.
	"""

	def test_it_goes_back_even_though_the_parameters_differ(self):
		first = self.commit({'Title': 'P', 'Parameters': {'n': {'type': 'Z'}},
		                     'Numbers': {'1': '3.14'}})
		commit_table(self.table,
		             {'Title': 'P',
		              'Parameters': {'m': {'type': 'Z'}, 'k': {'type': 'Z'}},
		              'Numbers': {'1': {'2': '3.14'}}},
		             author=self.alice, base=first,
		             allow_parameter_change=True)
		restore_revision(self.table, first, author=self.alice)
		self.assertEqual(list(self.head_tree()['Parameters']), ['n'])


class HistoryView(RestoreBase):

	def setUp(self):
		super().setUp()
		self.first = self.commit({'Title': 'H', 'Numbers': {'1': '3.14159'}},
		                         message='first version')
		self.second = self.commit({'Title': 'H', 'Numbers': {'1': '2.71828'}},
		                          base=self.first, message='second version')

	def url(self):
		return '/revisions/%s' % (self.table.tid,)

	def test_anyone_may_read_the_history(self):
		r = self.client.get(self.url())
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'first version')
		self.assertContains(r, 'second version')

	def test_the_default_comparison_is_the_latest_change(self):
		r = self.client.get(self.url())
		self.assertContains(r, '-  &#x27;1&#x27;: &#x27;3.14159&#x27;')
		self.assertContains(r, '+  &#x27;1&#x27;: &#x27;2.71828&#x27;')

	def test_any_two_versions_can_be_compared(self):
		third = self.commit({'Title': 'H', 'Numbers': {'1': '1.61803'}},
		                    base=self.second, message='third version')
		r = self.client.get('%s?from=%s&to=%s'
		                    % (self.url(), self.first.pk, third.pk))
		self.assertContains(r, '-  &#x27;1&#x27;: &#x27;3.14159&#x27;')
		self.assertContains(r, '+  &#x27;1&#x27;: &#x27;1.61803&#x27;')
		#The version in between is skipped over, not shown as a step.
		self.assertNotContains(r, '2.71828')

	def test_comparing_a_version_with_itself_says_so(self):
		r = self.client.get('%s?from=%s&to=%s'
		                    % (self.url(), self.first.pk, self.first.pk))
		self.assertContains(r, 'Nothing differs')

	def test_a_nonsense_revision_id_does_not_break_the_page(self):
		r = self.client.get('%s?from=nonsense&to=9999999' % (self.url(),))
		self.assertEqual(r.status_code, 200)

	def test_an_unknown_table_is_a_404(self):
		self.assertEqual(self.client.get('/revisions/T99999').status_code, 404)


class RestoreThroughTheView(RestoreBase):

	def setUp(self):
		super().setUp()
		self.good = self.commit({'Title': 'H', 'Numbers': {'1': '3.14159'}})
		self.bad = self.commit({'Title': 'H', 'Numbers': {'1': '2.71828'}},
		                       base=self.good)

	def url(self):
		return '/revisions/%s' % (self.table.tid,)

	def head_numbers(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)['Numbers']

	def test_a_signed_out_reader_is_offered_the_login_and_writes_nothing(self):
		r = self.client.post(self.url(), {'restore': self.good.pk})
		self.assertEqual(r.status_code, 302)
		self.assertIn('/accounts/login/', r['Location'])
		self.assertEqual(self.head_numbers(), {'1': '2.71828'})

	def test_a_signed_in_account_can_restore(self):
		self.client.login(username='alice_h', password='pw-123456')
		r = self.client.post(self.url(), {'restore': self.good.pk})
		self.assertEqual(r.status_code, 302)
		self.assertEqual(self.head_numbers(), {'1': '3.14159'})

	def test_a_restore_by_an_ordinary_account_still_awaits_review(self):
		"""A restore is an edit, so it goes through the same gate."""
		self.client.login(username='alice_h', password='pw-123456')
		self.client.post(self.url(), {'restore': self.good.pk})
		self.table.refresh_from_db()
		self.assertNotEqual(self.table.reviewed_at_revision_id,
		                    self.table.head_revision_id)

	def test_a_restore_by_the_board_is_reviewed_at_once(self):
		self.client.login(username='chair_h', password='pw-123456')
		self.client.post(self.url(), {'restore': self.good.pk})
		self.table.refresh_from_db()
		self.assertEqual(self.table.reviewed_at_revision_id,
		                 self.table.head_revision_id)

	def test_restoring_something_that_is_not_a_revision_writes_nothing(self):
		self.client.login(username='alice_h', password='pw-123456')
		r = self.client.post(self.url(), {'restore': '9999999'})
		self.assertEqual(r.status_code, 302)
		self.assertEqual(self.head_numbers(), {'1': '2.71828'})

	def test_a_revision_of_another_table_cannot_be_restored_here(self):
		"""Otherwise one table's history is a way to overwrite another's."""
		other = Table.objects.create(tid='T922', tid_int=922, title='Other',
		                             url='Other922')
		theirs = commit_table(other, {'Title': 'Other', 'Numbers': {'1': '9'}},
		                      author=self.alice).revision
		self.client.login(username='alice_h', password='pw-123456')
		self.client.post(self.url(), {'restore': theirs.pk})
		self.assertEqual(self.head_numbers(), {'1': '2.71828'})


class DiffsAreReadable(TestCase):
	"""A diff of a table is a few changes scattered through a thousand entries.

	Run together in one block, the reader has to find the boundaries; without
	colour, they have to scan for leading signs. Both are work the page can do.
	"""

	def setUp(self):
		from .views import _diff_blocks

		self.blocks = _diff_blocks(
			'--- a\n+++ b\n'
			'@@ -1,3 +1,3 @@\n Title: X\n-  a: 1\n+  a: 2\n'
			'@@ -40,2 +40,2 @@\n-  z: 8\n+  z: 9\n')

	def test_one_block_per_hunk(self):
		self.assertEqual(len(self.blocks), 2)

	def test_each_block_keeps_its_header(self):
		self.assertTrue(self.blocks[0]['header'].startswith('@@'))

	def test_lines_say_what_they_are(self):
		kinds = [line['kind'] for line in self.blocks[0]['lines']]
		self.assertEqual(kinds, ['context', 'removed', 'added'])

	def test_the_sign_is_stripped_from_the_text(self):
		"""It is put back by the template, so colour is not the only signal."""
		added = [l for l in self.blocks[0]['lines'] if l['kind'] == 'added']
		self.assertEqual(added[0]['text'], '  a: 2')

	def test_file_headers_are_dropped(self):
		self.assertNotIn('---', str(self.blocks))

	def test_an_empty_diff_gives_no_blocks(self):
		from .views import _diff_blocks

		self.assertEqual(_diff_blocks(''), [])


class FilesBelongToARevision(RestoreBase):
	"""The manifest is complete at every revision, so a file is not one thing
	the table has -- it is one thing per version. A reader not told which will
	assume the code shown produced the numbers shown."""

	def setUp(self):
		super().setUp()
		self.first = commit_table(
			self.table, {'Title': 'H', 'Numbers': {'1': '3.14'}},
			author=self.alice,
			files={'generate.sage': 'v1', 'notes.txt': 'unchanged'}).revision
		self.second = commit_table(
			self.table, {'Title': 'H', 'Numbers': {'1': '3.15'}},
			author=self.alice, base=self.first,
			files={'generate.sage': 'v2'}).revision

	def files_at(self, revision):
		from .views import _files_with_history

		return {f['name']: f for f in _files_with_history(self.table, revision)}

	def test_a_changed_file_is_dated_to_the_revision_that_changed_it(self):
		shown = self.files_at(self.second)
		self.assertEqual(shown['generate.sage']['since'].pk, self.second.pk)
		self.assertTrue(shown['generate.sage']['changed_here'])

	def test_an_untouched_file_keeps_its_older_date(self):
		"""The point: notes.txt is carried, not rewritten, by the second edit."""
		shown = self.files_at(self.second)
		self.assertEqual(shown['notes.txt']['since'].pk, self.first.pk)
		self.assertFalse(shown['notes.txt']['changed_here'])

	def test_the_first_version_of_a_file_is_marked_as_original(self):
		shown = self.files_at(self.first)
		self.assertTrue(shown['generate.sage']['is_original'])

	def test_an_older_revision_shows_the_file_it_had(self):
		shown = self.files_at(self.first)
		self.assertEqual(shown['generate.sage']['blob'].text(), 'v1')

	def test_a_later_change_does_not_leak_backwards(self):
		"""Looking at March must not date a file to a change made in April."""
		shown = self.files_at(self.first)
		self.assertEqual(shown['generate.sage']['since'].pk, self.first.pk)
