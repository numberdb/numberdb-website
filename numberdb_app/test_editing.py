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


class CreatingTables(TestCase):
	"""Tables come into existence here, not in the data repository."""

	def setUp(self):
		self.user = User.objects.create_user('creator', password='pw-123456')
		self.client.login(username='creator', password='pw-123456')

	DOC = ('Title: Zeros of the Airy function\n'
	       'Definition: >\n'
	       '  The zeros.\n'
	       'Parameters:\n'
	       '  n:\n'
	       '    type: Z\n'
	       'Data properties:\n'
	       '  type: R\n'
	       'Numbers:\n'
	       "  '1': -2.33810741045976703849\n")

	def test_the_form_offers_a_skeleton(self):
		r = self.client.get('/new')
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'Data properties')
		self.assertContains(r, 'Display properties')

	def test_creating_allocates_the_next_identifier(self):
		from .models import Table
		highest = max(t.tid_int for t in Table.objects.all()) if Table.objects.exists() else 0
		r = self.client.post('/new', {'table': self.DOC})
		self.assertEqual(r.status_code, 302)
		table = Table.objects.get(title='Zeros of the Airy function')
		self.assertEqual(table.tid_int, highest + 1)
		self.assertEqual(table.tid, 'T%d' % (highest + 1,))

	def test_the_slug_comes_from_the_title(self):
		from .models import Table
		self.client.post('/new', {'table': self.DOC})
		table = Table.objects.get(title='Zeros of the Airy function')
		self.assertEqual(table.url, 'Zeros_of_the_Airy_function')

	def test_a_second_table_of_the_same_name_is_refused_readably(self):
		"""Titles are unique, so this must be a message and not a 500."""
		from .models import Table
		self.client.post('/new', {'table': self.DOC})
		before = Table.objects.count()
		r = self.client.post('/new', {'table': self.DOC})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'already exists')
		self.assertEqual(Table.objects.count(), before)

	def test_titles_that_differ_only_in_punctuation_get_distinct_addresses(self):
		from .models import Table
		self.client.post('/new', {'table': self.DOC})
		other = self.DOC.replace('Zeros of the Airy function',
		                         'Zeros of the Airy function!')
		self.client.post('/new', {'table': other})
		urls = sorted(Table.objects.filter(title__startswith='Zeros of the Airy')
		              .values_list('url', flat=True))
		self.assertEqual(urls, ['Zeros_of_the_Airy_function',
		                        'Zeros_of_the_Airy_function_2'])

	def test_the_first_revision_records_who_made_it(self):
		from .models import Table
		self.client.post('/new', {'table': self.DOC, 'message': 'first'})
		table = Table.objects.get(title='Zeros of the Airy function')
		self.assertIsNotNone(table.head_revision)
		self.assertEqual(table.head_revision.author_id, self.user.pk)
		self.assertEqual(table.head_revision.message, 'first')

	def test_the_numbers_are_built_and_left_unreviewed(self):
		from .models import Number, Table
		self.client.post('/new', {'table': self.DOC})
		table = Table.objects.get(title='Zeros of the Airy function')
		rows = Number.objects.filter(table=table)
		self.assertEqual(rows.count(), 1)
		self.assertFalse(rows.first().reviewed)

	def test_a_table_without_a_title_is_refused(self):
		from .models import Table
		before = Table.objects.count()
		r = self.client.post('/new', {'table': 'Definition: no title here\n'})
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'needs a Title')
		self.assertEqual(Table.objects.count(), before)

	def test_previewing_creates_nothing(self):
		from .models import Table
		before = Table.objects.count()
		r = self.client.post('/new', {'table': self.DOC, 'action': 'preview'})
		self.assertEqual(r.status_code, 200)
		self.assertEqual(Table.objects.count(), before)

	def test_anonymous_cannot_create(self):
		self.client.logout()
		r = self.client.post('/new', {'table': self.DOC})
		self.assertEqual(r.status_code, 302)
		self.assertIn('/accounts/login/', r['Location'])


class MacrosAreResolvedBeforeEditing(TestCase):
	"""Thirty tables keep their numbers in a sibling file, referenced by a
	macro. The editor must never show that macro, because saving it would
	replace every value in the table with the text of the reference."""

	def setUp(self):
		from .models import TableData
		self.table = Table.objects.create(tid='T913', tid_int=913,
		                                  title='Macro probe', url='Macro913')
		TableData.objects.create(
			table=self.table,
			#What the repository file says.
			raw_yaml='Title: Macro probe\nNumbers: INPUT{numbers.yaml}\n',
			#What it means, once resolved. This is what the site renders.
			full_yaml=("Title: Macro probe\n"
			           "Parameters:\n  n:\n    type: Z\n"
			           "Numbers:\n  '1': 3.14159265358979323846\n"
			           "  '2': 2.71828182845904523536\n"))
		self.user = User.objects.create_user('macro_user', password='pw-123456')
		self.client.login(username='macro_user', password='pw-123456')

	def test_the_editor_shows_the_numbers_not_the_reference(self):
		r = self.client.get('/edit/%s' % self.table.tid)
		self.assertEqual(r.status_code, 200)
		self.assertNotContains(r, 'INPUT{numbers.yaml}')
		self.assertContains(r, '3.14159265358979323846')

	def test_saving_what_the_editor_offered_keeps_every_value(self):
		from .editing import tree_of
		from .models import Number
		r = self.client.get('/edit/%s' % self.table.tid)
		offered = r.context['table_yaml']
		self.client.post('/edit/%s' % self.table.tid, {'table': offered})
		self.table.refresh_from_db()
		numbers = tree_of(self.table.head_revision)['Numbers']
		self.assertEqual(set(numbers), {'1', '2'})
		self.assertEqual(Number.objects.filter(table=self.table).count(), 2)


class EntryAddresses(TestCase):
	"""A single value has to have an address the server can resolve.

	The fragment form is invisible to the server by the definition of HTTP, so
	a stale citation used to load the page and quietly scroll nowhere.
	"""

	def setUp(self):
		from .models import TableData
		self.table = Table.objects.create(tid='T914', tid_int=914,
		                                  title='Address probe', url='Addr914')
		doc = ("Title: Address probe\n"
		       "Parameters:\n  n:\n    type: Z\n"
		       "Numbers:\n"
		       "  '6': 3.14159265358979323846\n"
		       "  '7': 2.71828182845904523536\n")
		TableData.objects.create(table=self.table, raw_yaml=doc, full_yaml=doc)

	@staticmethod
	def _focused(response):
		"""Rows carrying the focus class, ignoring the stylesheet that defines
		it -- which appears on every page and made assertNotContains useless."""
		import re
		return re.findall(r'class="table-block table-block-focused"',
		                  response.content.decode())

	def test_a_known_entry_is_marked(self):
		r = self.client.get('/%s?entry=6' % self.table.url)
		self.assertEqual(r.status_code, 200)
		self.assertEqual(len(self._focused(r)), 1)

	def test_an_unknown_entry_says_so_instead_of_failing_silently(self):
		r = self.client.get('/%s?entry=999' % self.table.url)
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'no entry')
		self.assertEqual(self._focused(r), [])

	def test_the_table_is_still_shown_when_the_entry_is_gone(self):
		"""A broken citation should not cost the reader the page."""
		r = self.client.get('/%s?entry=999' % self.table.url)
		self.assertContains(r, 'Address probe')

	def test_no_entry_asked_for_changes_nothing(self):
		r = self.client.get('/%s' % self.table.url)
		self.assertEqual(r.status_code, 200)
		self.assertEqual(self._focused(r), [])

	def test_it_works_by_identifier_as_well_as_slug(self):
		r = self.client.get('/%s?entry=6' % self.table.tid)
		self.assertEqual(r.status_code, 200)
		self.assertEqual(len(self._focused(r)), 1)

	def test_a_slash_in_the_identity_survives_the_query_string(self):
		"""6736 identities contain one, because parameters are rationals."""
		from .models import TableData
		doc = ("Title: Rational probe\n"
		       "Parameters:\n  q:\n    type: Q\n"
		       "Numbers:\n  '18/11': 1.63636363636363636364\n")
		t = Table.objects.create(tid='T915', tid_int=915,
		                         title='Rational probe', url='Rat915')
		TableData.objects.create(table=t, raw_yaml=doc, full_yaml=doc)
		r = self.client.get('/%s?entry=18/11' % t.url)
		self.assertEqual(r.status_code, 200)
		self.assertEqual(len(self._focused(r)), 1)


class NamedEntryAddresses(TestCase):
	"""A positional identity can silently come to mean a different number.

	With parameters a and b nested one way, entry 1,2 is (a=1, b=2). Nest them
	the other way and 1,2 still exists and is (a=2, b=1): the citation does not
	break, it lies. Naming the parameters removes the ambiguity.
	"""

	def setUp(self):
		from .models import TableData
		doc = ("Title: Named probe\n"
		       "Parameters:\n"
		       "  a:\n    type: Z\n"
		       "  b:\n    type: Z\n"
		       "Numbers:\n"
		       "  '1':\n    '2': 3.14159265358979323846\n"
		       "  '2':\n    '1': 2.71828182845904523536\n")
		self.table = Table.objects.create(tid='T916', tid_int=916,
		                                  title='Named probe', url='Named916')
		TableData.objects.create(table=self.table, raw_yaml=doc, full_yaml=doc)

	@staticmethod
	def _focused(response):
		import re
		return re.findall(r'class="table-block table-block-focused"',
		                  response.content.decode())

	def test_a_named_citation_resolves(self):
		r = self.client.get('/%s?entry=a=1,b=2' % self.table.url)
		self.assertEqual(len(self._focused(r)), 1)

	def test_the_order_written_does_not_matter(self):
		"""Which is the entire point: order is what positional identity leaks."""
		r = self.client.get('/%s?entry=b=2,a=1' % self.table.url)
		self.assertEqual(len(self._focused(r)), 1)

	def test_a_positional_citation_still_resolves(self):
		"""Everything written before today is in this form."""
		r = self.client.get('/%s?entry=1,2' % self.table.url)
		self.assertEqual(len(self._focused(r)), 1)

	def test_an_unknown_parameter_name_is_refused(self):
		r = self.client.get('/%s?entry=a=1,zzz=2' % self.table.url)
		self.assertEqual(self._focused(r), [])
		self.assertContains(r, 'no parameter')

	def test_naming_distinguishes_entries_that_positional_confuses(self):
		a1b2 = self.client.get('/%s?entry=a=1,b=2' % self.table.url)
		a2b1 = self.client.get('/%s?entry=a=2,b=1' % self.table.url)
		self.assertEqual(len(self._focused(a1b2)), 1)
		self.assertEqual(len(self._focused(a2b1)), 1)
		#Different entries, and the citations say which is which.
		self.assertIn('3.14159265358979323846', a1b2.content.decode())
		self.assertIn('2.71828182845904523536', a2b1.content.decode())
