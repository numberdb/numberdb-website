"""Everything derived from a document must agree with it after an edit.

One bug, found by adding a tag: a tag lived in the document and as a Tag row,
and only the document was written. The shape is general -- a table's facts are
stored twice, once in the revision and once in whatever column, row or index
serves a page fast -- and every place that happens is somewhere an edit can be
recorded and invisible.

So this file does not test tags. It tests the invariant: after a commit, every
derived thing matches the document it was derived from. A new derived column
that nobody remembers to update fails here rather than in somebody's face.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Table


class DerivedStateAgreesWithTheDocument(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('deriver', password='pw-123456')
		self.table = create_table(
			{'Title': 'Derived probe',
			 'Definition': 'What these numbers are.',
			 'Tags': ['ring', 'analysis'],
			 'Parameters': {'n': {'type': 'Z'}},
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'},
			             {'params': {'n': '2'}, 'number': '2.71'}]},
			author=self.user,
		via='orm')

	def commit(self, changes):
		from .editing import commit_table, tree_of

		tree = dict(tree_of(self.table.head_revision))
		tree.update(changes)
		commit_table(self.table, tree, author=self.user, message='a change', via='orm')
		self.table.refresh_from_db()
		return tree

	def document(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	#-- the invariants -------------------------------------------------

	def test_the_title_column_matches(self):
		self.commit({'Title': 'Renamed probe'})
		self.assertEqual(self.table.title, 'Renamed probe')
		self.assertEqual(self.table.title_lowercase, 'renamed probe')

	def test_the_tags_match(self):
		self.commit({'Tags': ['analysis', 'geometry']})
		self.assertEqual(sorted(t.name for t in self.table.tags.all()),
		                 ['analysis', 'geometry'])

	def test_the_number_count_matches(self):
		self.commit({'Numbers': [{'params': {'n': str(n)}, 'number': '1.%d' % n}
		                         for n in range(1, 6)]})
		self.assertEqual(self.table.number_count, 5)

	def test_the_stored_document_matches(self):
		"""TableData is what the page renders from; a revision the page does
		not show is an edit that was recorded and is invisible."""
		from .models import TableData

		self.commit({'Definition': 'Something else entirely.'})
		data = TableData.objects.get(table=self.table)
		self.assertIn('Something else entirely', data.full_yaml)

	def test_the_number_rows_match(self):
		from .models import Number

		self.commit({'Numbers': [{'params': {'n': '1'}, 'number': '9.99'}]})
		texts = [n.exact_text for n in Number.objects.filter(table=self.table)]
		self.assertEqual(texts, ['9.99'])

	def test_the_word_index_matches(self):
		"""Renaming a table used to change its page and nothing else."""
		self.commit({'Title': 'Findable by this word'})
		self.table.refresh_from_db()
		self.assertIn('Findable', self.table.search.weight_A_text)

	def test_the_overview_row_exists_and_matches(self):
		"""The overview page reads TableMetrics, so a table without a row is
		a table missing from the page. Every table built overnight was
		missing until somebody ran `refresh_table_metrics` by hand."""
		from .models import TableMetrics

		metrics = TableMetrics.objects.get(table=self.table)
		self.assertEqual(metrics.entry_count, 2)
		self.assertEqual(metrics.edit_count, self.table.revisions.count())
		self.assertEqual(metrics.data_type, 'R')

		self.commit({'Numbers': [{'params': {'n': '1'}, 'number': '9.99'}]})
		metrics.refresh_from_db()
		self.assertEqual(metrics.entry_count, 1)
		self.assertEqual(metrics.edit_count, self.table.revisions.count())

	def test_every_tag_counter_matches(self):
		from django.db.models import Sum

		from .models import Tag

		self.commit({'Tags': ['analysis']})
		for tag in Tag.objects.all():
			with self.subTest(tag=tag.name):
				#Published tables: a draft is not part of what a tag says it
				#reaches. See test_tags_hide_drafts.
				self.assertEqual(tag.table_count, tag.public_tables.count())
				self.assertEqual(
					tag.number_count,
					tag.public_tables.aggregate(t=Sum('number_count'))['t']
					or 0)

	def test_a_tag_created_here_is_as_complete_as_one_the_pipeline_built(self):
		"""The test that would have caught the reported bug, stated as what it
		is: a tag made on the site must be a whole tag."""
		from .models import Tag

		self.commit({'Tags': ['ring', 'brand new subject']})
		made = Tag.objects.get(name='brand new subject')
		self.assertTrue(made.name_lowercase)
		self.assertTrue(made.search_vector)
		self.assertEqual(made.table_count, 1)
		self.assertIn(self.table, list(made.tables.all()))


class TheNavigationCountsWhatTheQueueLists(TestCase):
	"""The number and the list are the same list.

	A count computed separately from what it counts is a count that will one
	day disagree with it, and the number in the navigation is the one a reader
	believes -- they only open the queue when it says something is there.
	"""

	def setUp(self):
		from django.contrib.auth.models import Group

		from .permissions import BOARD_GROUP

		User = get_user_model()
		self.board = User.objects.create_user('navboard', password='x')
		group, _ = Group.objects.get_or_create(name=BOARD_GROUP)
		self.board.groups.add(group)
		self.other = User.objects.create_user('navother', password='x')
		self.author = User.objects.create_user('navauthor')

	def a_table(self, tid, published, ready):
		from .editing import commit_table

		table = Table.objects.create(
			tid=tid, tid_int=int(tid[1:]), url=tid.lower(), title='Table ' + tid,
			published=published, ready_for_review=ready, created_by=self.author)
		commit_table(table, {'Title': 'Table ' + tid, 'Numbers': {'1': '2'},
		                     'Data properties': {'type': 'Z'}},
		             author=self.author, message='m', via='orm')
		table.refresh_from_db()
		return table

	def nav(self, user):
		client = Client()
		client.force_login(user)
		return client.get('/', HTTP_HOST='numberdb.org')

	def test_the_count_is_the_length_of_the_queue(self):
		from .review import waiting_for_review

		self.a_table('T730', published=False, ready=True)
		self.a_table('T731', published=True, ready=False)
		response = self.nav(self.board)
		self.assertEqual(response.context['tables_waiting_for_review'],
		                 len(waiting_for_review()))

	def test_it_shows_in_the_bar(self):
		self.a_table('T732', published=False, ready=True)
		body = self.nav(self.board).content.decode()
		self.assertIn('Review&nbsp;(1)', body)

	def test_a_draft_nobody_offered_is_not_counted(self):
		#It would put every half-made table in the queue, which is what the
		#ready_for_review flag exists to stop.
		self.a_table('T733', published=False, ready=False)
		self.assertEqual(self.nav(self.board).context['tables_waiting_for_review'], 0)

	def test_nothing_waiting_shows_no_number(self):
		body = self.nav(self.board).content.decode()
		self.assertIn('>Review</a>', body.replace('\n', '').replace('  ', ''))

	def test_somebody_who_cannot_review_is_told_nothing(self):
		self.a_table('T734', published=False, ready=True)
		response = self.nav(self.other)
		self.assertEqual(response.context['tables_waiting_for_review'], 0)
		self.assertNotIn('db:review-queue', response.content.decode())
