"""Tests for committing an edited table.

The cases that matter are the concurrent ones. A stale write that quietly wins
leaves a table looking perfectly normal with somebody's correction missing, so
each of these checks not only what was written but what survived.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .editing import StaleEdit, commit_table, dump_tree, tree_of
from .models import Table, TableRevision


class CommitBase(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T900', tid_int=900,
		                                  title='Probe', url='Probe')
		self.alice = User.objects.create(username='alice')
		self.bob = User.objects.create(username='bob')

	def commit(self, tree, who=None, base=None, message=''):
		return commit_table(self.table, tree, author=who or self.alice,
		                    message=message, base=base)

	def head_tree(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)


class FirstRevision(CommitBase):

	def test_a_table_with_no_history_accepts_one(self):
		out = self.commit({'Title': 'Probe', 'Numbers': {'1': '3.14'}})
		self.assertFalse(out.merged)
		self.assertIsNone(out.revision.parent)
		self.assertIsNone(out.revision.base)
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision_id, out.revision.pk)

	def test_head_advances(self):
		first = self.commit({'Title': 'A'}).revision
		second = self.commit({'Title': 'B'}, base=first).revision
		self.assertEqual(second.parent_id, first.pk)
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision_id, second.pk)


class NoOpEdits(CommitBase):

	def test_saving_without_changing_anything_creates_no_revision(self):
		first = self.commit({'Title': 'A', 'Numbers': {'1': '3.14'}}).revision
		before = TableRevision.objects.count()
		out = self.commit({'Title': 'A', 'Numbers': {'1': '3.14'}}, base=first)
		self.assertTrue(out.unchanged)
		self.assertEqual(out.revision.pk, first.pk)
		self.assertEqual(TableRevision.objects.count(), before)


class ConcurrentEdits(CommitBase):
	"""Two people editing at once, which is the case this exists for."""

	def setUp(self):
		super().setUp()
		self.start = self.commit(
			{'Title': 'Probe', 'Numbers': {'5': '1.234', '17': '5.678'}}
		).revision

	def test_disjoint_edits_merge_without_anybody_noticing(self):
		#Bob commits first.
		commit_table(self.table, {'Title': 'Probe',
		                          'Numbers': {'5': '1.234', '17': '9.999'}},
		             author=self.bob, base=self.start)
		#Alice was editing from the same start and only touched entry 5.
		out = commit_table(self.table, {'Title': 'Probe',
		                                'Numbers': {'5': '1.111', '17': '5.678'}},
		                   author=self.alice, base=self.start)
		self.assertTrue(out.merged)
		#Both survive. This is the assertion the whole design is for.
		self.assertEqual(self.head_tree()['Numbers'],
		                 {'5': '1.111', '17': '9.999'})

	def test_the_merge_records_where_it_came_from(self):
		bob = commit_table(self.table,
		                   {'Title': 'Probe',
		                    'Numbers': {'5': '1.234', '17': '9.999'}},
		                   author=self.bob, base=self.start).revision
		out = commit_table(self.table,
		                   {'Title': 'Probe',
		                    'Numbers': {'5': '1.111', '17': '5.678'}},
		                   author=self.alice, base=self.start)
		#Parent is what it was applied to; base is what Alice actually saw.
		self.assertEqual(out.revision.parent_id, bob.pk)
		self.assertEqual(out.revision.base_id, self.start.pk)
		self.assertNotEqual(out.revision.parent_id, out.revision.base_id)

	def test_conflicting_edits_write_nothing(self):
		commit_table(self.table,
		             {'Title': 'Probe', 'Numbers': {'5': '2.000', '17': '5.678'}},
		             author=self.bob, base=self.start)
		before = TableRevision.objects.count()
		head_before = self.head_tree()
		with self.assertRaises(StaleEdit) as caught:
			commit_table(self.table,
			             {'Title': 'Probe',
			              'Numbers': {'5': '3.000', '17': '5.678'}},
			             author=self.alice, base=self.start)
		#Nothing half-written, and Bob's version still stands.
		self.assertEqual(TableRevision.objects.count(), before)
		self.assertEqual(self.head_tree(), head_before)
		self.assertEqual(caught.exception.conflicts[0].path, ('Numbers', '5'))

	def test_an_edit_already_contained_in_head_is_a_no_op(self):
		"""Alice and Bob happened to make the same correction."""
		same = {'Title': 'Probe', 'Numbers': {'5': '1.234', '17': '7.777'}}
		commit_table(self.table, same, author=self.bob, base=self.start)
		before = TableRevision.objects.count()
		out = commit_table(self.table, same, author=self.alice,
		                   base=self.start)
		self.assertTrue(out.unchanged)
		self.assertEqual(TableRevision.objects.count(), before)

	def test_editing_without_saying_what_you_started_from(self):
		"""base=None on a table with history means 'apply to head'."""
		commit_table(self.table,
		             {'Title': 'Probe', 'Numbers': {'5': '1.234', '17': '9.999'}},
		             author=self.bob, base=self.start)
		out = commit_table(self.table, {'Title': 'Overwritten'},
		                   author=self.alice, base=None)
		self.assertFalse(out.merged)
		self.assertEqual(self.head_tree(), {'Title': 'Overwritten'})


class Serialisation(CommitBase):

	def test_key_order_survives_a_round_trip(self):
		tree = {'ID': 'T900', 'Title': 'Probe', 'Definition': 'd',
		        'Numbers': {'1': '3.14'}}
		out = self.commit(tree)
		self.assertEqual(list(tree_of(out.revision)),
		                 ['ID', 'Title', 'Definition', 'Numbers'])

	def test_values_are_not_coerced_by_the_loader(self):
		"""`complete: no` must come back as the word, not as False."""
		out = self.commit({'Data properties': {'complete': 'no'}})
		self.assertEqual(tree_of(out.revision)['Data properties']['complete'],
		                 'no')

	def test_identical_trees_produce_identical_content(self):
		a = dump_tree({'Title': 'x', 'Numbers': {'1': 'a'}})
		b = dump_tree({'Title': 'x', 'Numbers': {'1': 'a'}})
		self.assertEqual(TableRevision.digest_of(a),
		                 TableRevision.digest_of(b))


class Attribution(CommitBase):

	def test_a_machine_written_edit_says_so(self):
		out = self.commit({'Title': 'A'})
		out = commit_table(self.table, {'Title': 'B'}, author=self.alice,
		                   base=out.revision, produced_by='some-model/1.0')
		self.assertEqual(out.revision.produced_by, 'some-model/1.0')
		self.assertEqual(out.revision.author_id, self.alice.pk)


class EditView(TestCase):
	"""The editor, end to end through HTTP."""

	def setUp(self):
		from django.contrib.auth.models import Group
		from .permissions import BOARD_GROUP
		self.table = Table.objects.create(tid='T910', tid_int=910,
		                                  title='View probe', url='View910')
		from .models import TableData
		TableData.objects.create(table=self.table, raw_yaml='Title: View probe\n')
		self.alice = User.objects.create_user('alice_v', password='pw-123456')
		self.chair = User.objects.create_user('chair_v', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])

	DOC = ('Title: View probe\n'
	       'Parameters:\n'
	       '  n:\n'
	       '    type: Z\n'
	       'Numbers:\n'
	       "  '1': 3.14159265358979323846\n")

	def url(self):
		return '/edit/%s' % (self.table.tid,)

	def test_anonymous_is_sent_to_the_login_page(self):
		r = self.client.get(self.url())
		self.assertEqual(r.status_code, 302)
		self.assertIn('/accounts/login/', r['Location'])

	def test_an_account_sees_the_editor(self):
		self.client.login(username='alice_v', password='pw-123456')
		r = self.client.get(self.url())
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'Editing')
		self.assertContains(r, 'What did you change?')

	def test_saving_creates_a_revision_and_redirects_to_the_table(self):
		self.client.login(username='alice_v', password='pw-123456')
		r = self.client.post(self.url(), {'table': self.DOC,
		                                  'message': 'first version'})
		self.assertEqual(r.status_code, 302)
		self.assertIn(self.table.url, r['Location'])
		self.table.refresh_from_db()
		self.assertIsNotNone(self.table.head_revision)
		self.assertEqual(self.table.head_revision.author_id, self.alice.pk)
		self.assertEqual(self.table.head_revision.message, 'first version')

	def test_an_ordinary_edit_does_not_count_as_reviewed(self):
		self.client.login(username='alice_v', password='pw-123456')
		self.client.post(self.url(), {'table': self.DOC})
		self.table.refresh_from_db()
		self.assertIsNone(self.table.reviewed_at_revision)

	def test_a_board_members_edit_is_reviewed_on_save(self):
		"""Otherwise the queue is one person's edits waiting for that person."""
		self.client.login(username='chair_v', password='pw-123456')
		self.client.post(self.url(), {'table': self.DOC})
		self.table.refresh_from_db()
		self.assertEqual(self.table.reviewed_at_revision_id,
		                 self.table.head_revision_id)

	def test_malformed_yaml_saves_nothing_and_says_so(self):
		self.client.login(username='alice_v', password='pw-123456')
		r = self.client.post(self.url(), {'table': 'Title: [unclosed\n'})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'YAML format error')
		self.table.refresh_from_db()
		self.assertIsNone(self.table.head_revision)

	def test_a_conflicting_save_writes_nothing(self):
		self.client.login(username='alice_v', password='pw-123456')
		self.client.post(self.url(), {'table': self.DOC})
		self.table.refresh_from_db()
		start = self.table.head_revision

		#Somebody else changes the same entry.
		commit_table(self.table,
		             {'Title': 'View probe',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': {'1': '2.0'}},
		             author=self.chair, base=start)
		self.table.refresh_from_db()
		theirs = self.table.head_revision

		mine = self.DOC.replace('3.14159265358979323846', '9.0')
		r = self.client.post(self.url(), {'table': mine,
		                                  'base': start.digest})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'Nothing was saved')
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision_id, theirs.pk)

	def test_a_disjoint_save_merges_and_says_so(self):
		self.client.login(username='alice_v', password='pw-123456')
		doc = self.DOC + "  '2': 2.71828182845904523536\n"
		self.client.post(self.url(), {'table': doc})
		self.table.refresh_from_db()
		start = self.table.head_revision

		commit_table(self.table,
		             {'Title': 'View probe',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': {'1': '3.14159265358979323846',
		                          '2': '9.99'}},
		             author=self.chair, base=start)

		mine = doc.replace('3.14159265358979323846', '3.15')
		r = self.client.post(self.url(), {'table': mine,
		                                  'base': start.digest}, follow=True)
		self.assertEqual(r.status_code, 200)
		self.table.refresh_from_db()
		from .editing import tree_of
		numbers = tree_of(self.table.head_revision)['Numbers']
		#Both survive.
		self.assertEqual(numbers['1'], '3.15')
		self.assertEqual(numbers['2'], '9.99')


class PreviewBeforeSaving(TestCase):
	"""Nothing is written until the author asks for it."""

	def setUp(self):
		from .models import TableData
		self.table = Table.objects.create(tid='T911', tid_int=911,
		                                  title='Draft probe', url='Draft911')
		TableData.objects.create(table=self.table, raw_yaml='Title: Draft probe\n')
		self.user = User.objects.create_user('drafter', password='pw-123456')
		self.client.login(username='drafter', password='pw-123456')

	DOC = ('Title: Draft probe\n'
	       'Parameters:\n'
	       '  n:\n'
	       '    type: Z\n'
	       'Numbers:\n'
	       "  '1': 3.14159265358979323846\n")

	def url(self):
		return '/edit/%s' % (self.table.tid,)

	def test_previewing_saves_nothing(self):
		r = self.client.post(self.url(), {'table': self.DOC,
		                                  'action': 'preview'})
		self.assertEqual(r.status_code, 200)
		self.table.refresh_from_db()
		self.assertIsNone(self.table.head_revision)
		self.assertEqual(TableRevision.objects.filter(table=self.table).count(), 0)

	def test_the_preview_shows_the_edited_content_not_the_saved_one(self):
		self.client.post(self.url(), {'table': self.DOC, 'action': 'save'})
		edited = self.DOC.replace('Draft probe', 'A different title')
		r = self.client.post(self.url(), {'table': edited, 'action': 'preview'})
		self.assertContains(r, 'A different title')

	def test_showing_changes_saves_nothing_and_reports_the_difference(self):
		self.client.post(self.url(), {'table': self.DOC, 'action': 'save'})
		self.table.refresh_from_db()
		head = self.table.head_revision
		edited = self.DOC.replace('3.14159265358979323846', '3.14159')
		r = self.client.post(self.url(), {'table': edited, 'action': 'diff',
		                                  'base': head.digest})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'Your changes')
		self.assertContains(r, '3.14159265358979323846')
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision_id, head.pk)

	def test_showing_changes_when_nothing_changed(self):
		self.client.post(self.url(), {'table': self.DOC, 'action': 'save'})
		self.table.refresh_from_db()
		r = self.client.post(self.url(),
		                     {'table': self.table.head_revision.content,
		                      'action': 'diff',
		                      'base': self.table.head_revision.digest})
		self.assertContains(r, 'No changes yet')

	def test_saving_still_saves(self):
		"""The default action, so a plain enter in a text field still works."""
		r = self.client.post(self.url(), {'table': self.DOC})
		self.assertEqual(r.status_code, 302)
		self.table.refresh_from_db()
		self.assertIsNotNone(self.table.head_revision)

	def test_a_malformed_document_previews_the_error_without_saving(self):
		r = self.client.post(self.url(), {'table': 'Title: [oops\n',
		                                  'action': 'preview'})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'YAML format error')
		self.table.refresh_from_db()
		self.assertIsNone(self.table.head_revision)


class ReviewInterface(TestCase):
	"""Confirming is what admits changed values back into search by number."""

	def setUp(self):
		from django.contrib.auth.models import Group
		from .models import TableData
		from .permissions import BOARD_GROUP
		self.table = Table.objects.create(tid='T912', tid_int=912,
		                                  title='Review probe', url='Review912')
		TableData.objects.create(table=self.table, raw_yaml='')
		self.author = User.objects.create_user('author_r', password='pw-123456')
		self.chair = User.objects.create_user('chair_r', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])

	DOC = {'Title': 'Review probe',
	       'Parameters': {'n': {'type': 'Z'}},
	       'Numbers': {'1': '3.14159265358979323846',
	                   '2': '2.71828182845904523536'}}

	def seed(self):
		first = commit_table(self.table, self.DOC, author=self.author)
		self.table.refresh_from_db()
		self.table.reviewed_at_revision = first.revision
		self.table.save(update_fields=['reviewed_at_revision'])
		changed = {'Title': 'Review probe',
		           'Parameters': {'n': {'type': 'Z'}},
		           'Numbers': {'1': '3.14159265358979323846',
		                       '2': '1.41421356237309504880'}}
		commit_table(self.table, changed, author=self.author,
		             base=first.revision)
		self.table.refresh_from_db()

	def test_the_queue_is_not_visible_to_ordinary_accounts(self):
		self.client.login(username='author_r', password='pw-123456')
		self.assertEqual(self.client.get('/review').status_code, 404)

	def test_the_queue_lists_a_table_with_outstanding_changes(self):
		self.seed()
		self.client.login(username='chair_r', password='pw-123456')
		r = self.client.get('/review')
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'Review probe')
		self.assertContains(r, '1 entry')

	def test_the_queue_is_empty_when_nothing_is_waiting(self):
		self.client.login(username='chair_r', password='pw-123456')
		r = self.client.get('/review')
		self.assertContains(r, 'Nothing is waiting')

	def test_the_review_page_names_the_changed_entries(self):
		self.seed()
		self.client.login(username='chair_r', password='pw-123456')
		r = self.client.get('/review/%s' % self.table.tid)
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'What changed')
		self.assertContains(r, '1.41421356237309504880')

	def test_confirming_admits_the_values_back_into_search(self):
		from .models import Number
		self.seed()
		changed = Number.objects.get(table=self.table, param=b'2')
		self.assertFalse(changed.reviewed)

		self.client.login(username='chair_r', password='pw-123456')
		self.table.refresh_from_db()
		r = self.client.post('/review/%s' % self.table.tid,
		                     {'head': self.table.head_revision.digest})
		self.assertEqual(r.status_code, 302)
		self.table.refresh_from_db()
		self.assertEqual(self.table.reviewed_at_revision_id,
		                 self.table.head_revision_id)
		changed.refresh_from_db()
		self.assertTrue(changed.reviewed)

	def test_a_change_arriving_mid_review_is_not_approved_unseen(self):
		self.seed()
		self.client.login(username='chair_r', password='pw-123456')
		self.table.refresh_from_db()
		stale_digest = self.table.head_revision.digest

		#Somebody edits again while the reviewer is reading.
		commit_table(self.table,
		             {'Title': 'Review probe',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': {'1': '9.99', '2': '1.41421356237309504880'}},
		             author=self.author)
		self.table.refresh_from_db()

		r = self.client.post('/review/%s' % self.table.tid,
		                     {'head': stale_digest}, follow=True)
		self.assertContains(r, 'changed again while you were looking')
		self.table.refresh_from_db()
		self.assertNotEqual(self.table.reviewed_at_revision_id,
		                    self.table.head_revision_id)
