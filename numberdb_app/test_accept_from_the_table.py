"""Accepting a table from the table's own page.

The queue is not where a table is read. Its prose renders on its page, a wrong
formula is visible there and nowhere else, and a reviewer who notices that
everything is right had to remember the number and go and find it in the queue
to say so. The button is put where the reading happens; the link beside it goes
to the diff, because "accept" and "what am I accepting" are one question.

It posts to the review page's own endpoint, so the guard against confirming a
revision that arrived while you were reading applies here too.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table
from .permissions import BOARD_GROUP


class TheAcceptBar(TestCase):

	def setUp(self):
		from django.contrib.auth.models import Group

		User = get_user_model()
		self.author = User.objects.create_user('author', password='x')
		self.board = User.objects.create_user('reviewer', password='x')
		group, _ = Group.objects.get_or_create(name=BOARD_GROUP)
		self.board.groups.add(group)

		#Offered for review, which is how a draft leaves the builder: the
		#queue lists a draft only when its author says it is finished, and
		#the button follows the queue.
		self.table = Table.objects.create(
			tid='T710', tid_int=710, url='t710', title='A draft table',
			published=False, ready_for_review=True, created_by=self.author)
		commit_table(self.table,
		             {'Title': 'A draft table', 'Numbers': {'1': '2'},
		              'Data properties': {'type': 'Z'}},
		             author=self.author, message='m', via='orm')
		self.table.refresh_from_db()

	def page(self, user):
		client = Client()
		if user is not None:
			client.force_login(user)
		return client.get('/T710', HTTP_HOST='numberdb.org')

	def test_a_board_member_is_offered_the_button(self):
		body = self.page(self.board).content.decode()
		self.assertIn('Accept and publish', body)

	def test_and_the_link_to_what_changed(self):
		body = self.page(self.board).content.decode()
		self.assertIn('/review/T710', body)
		self.assertIn('see what changed', body)

	def test_a_draft_nobody_has_offered_yet_shows_nothing(self):
		"""Half-built is not waiting, and inviting somebody to publish it is
		how an unfinished table goes public."""
		self.table.ready_for_review = False
		self.table.save(update_fields=['ready_for_review'])
		self.assertNotIn('Accept', self.page(self.board).content.decode())

	def test_the_author_is_not(self):
		"""It offers something only the board can do."""
		body = self.page(self.author).content.decode()
		self.assertNotIn('review-bar', body)

	def test_a_published_table_with_nothing_waiting_shows_nothing(self):
		from .editing import publish_table
		from .review import sync_review_flags

		publish_table(self.table)
		self.table.refresh_from_db()
		self.table.reviewed_at_revision = self.table.head_revision
		self.table.save(update_fields=['reviewed_at_revision'])
		sync_review_flags(self.table)
		body = self.page(self.board).content.decode()
		self.assertNotIn('review-bar', body)

	def test_a_published_table_with_unconfirmed_changes_does(self):
		from .editing import publish_table

		publish_table(self.table)
		self.table.refresh_from_db()
		self.table.reviewed_at_revision = None
		self.table.save(update_fields=['reviewed_at_revision'])
		body = self.page(self.board).content.decode()
		self.assertIn('Accept the changes', body)

	def test_accepting_publishes_and_comes_back_to_the_table(self):
		client = Client()
		client.force_login(self.board)
		response = client.post(
			'/review/T710',
			{'head': self.table.head_revision.digest, 'then': 'table'},
			HTTP_HOST='numberdb.org')
		self.assertEqual(response['Location'], '/T710')
		self.table.refresh_from_db()
		self.assertTrue(self.table.published)
		self.assertEqual(self.table.reviewed_by, self.board)

	def test_without_the_marker_it_still_goes_to_the_queue(self):
		#The queue is where a reviewer working through the queue belongs.
		client = Client()
		client.force_login(self.board)
		response = client.post(
			'/review/T710', {'head': self.table.head_revision.digest},
			HTTP_HOST='numberdb.org')
		self.assertEqual(response['Location'], '/review')

	def test_a_stale_digest_is_refused_from_here_too(self):
		"""The guard is the endpoint's, so it applies wherever the post came from."""
		client = Client()
		client.force_login(self.board)
		response = client.post(
			'/review/T710', {'head': 'not-the-head', 'then': 'table'},
			HTTP_HOST='numberdb.org')
		self.assertEqual(response['Location'], '/review/T710')
		self.table.refresh_from_db()
		self.assertFalse(self.table.published)

	def test_somebody_who_is_not_on_the_board_cannot_post_it(self):
		client = Client()
		client.force_login(self.author)
		response = client.post(
			'/review/T710',
			{'head': self.table.head_revision.digest, 'then': 'table'},
			HTTP_HOST='numberdb.org')
		self.assertEqual(response.status_code, 404)
		self.table.refresh_from_db()
		self.assertFalse(self.table.published)

	def test_the_table_leaves_the_review_queue(self):
		"""Accepting is what takes a table off the queue, from either route.

		The button publishes and confirms in one act, and confirming is what
		the queue is a list of. A table that publishes and stays listed would
		mean the two had come apart.
		"""
		client = Client()
		client.force_login(self.board)
		client.post('/review/T710',
		            {'head': self.table.head_revision.digest, 'then': 'table'},
		            HTTP_HOST='numberdb.org')
		queue = client.get('/review', HTTP_HOST='numberdb.org')
		listed = [row['table'].tid for row in queue.context['waiting']]
		self.assertNotIn('T710', listed)

	def test_it_is_in_the_queue_before_that(self):
		#So the test above is testing something.
		self.table.ready_for_review = True
		self.table.save(update_fields=['ready_for_review'])
		client = Client()
		client.force_login(self.board)
		queue = client.get('/review', HTTP_HOST='numberdb.org')
		listed = [row['table'].tid for row in queue.context['waiting']]
		self.assertIn('T710', listed)


class ATagPageSortsBySomethingItHas(TestCase):
	"""`entry_count` is the name of a sort; the column is `number_count`.

	The fallback branch passed the sort's name straight to `order_by`, so an
	unrecognised `sort_by` answered 500 instead of sorting the default way.
	Tag pages are public and crawled, and /tags/set+theory?sort_by=name was
	raising FieldError in the log.
	"""

	def setUp(self):
		from .models import Tag

		self.tag = Tag.objects.create(name='probe', name_lowercase='probe')
		table = Table.objects.create(
			tid='T711', tid_int=711, url='t711', title='In the tag',
			title_lowercase='in the tag', published=True, number_count=3)
		table.tags.add(self.tag)

	def get(self, query=''):
		return Client().get('/tags/%s%s' % (self.tag.url(), query),
		                    HTTP_HOST='numberdb.org')

	def test_the_plain_page_answers(self):
		self.assertEqual(self.get().status_code, 200)

	def test_an_unknown_sort_falls_back_instead_of_crashing(self):
		self.assertEqual(self.get('?sort_by=name').status_code, 200)

	def test_the_sorts_it_offers_all_answer(self):
		for sort in ('entry_count', 'id', 'title'):
			with self.subTest(sort=sort):
				self.assertEqual(self.get('?sort_by=%s' % sort).status_code, 200)


class TheButtonAppearsExactlyWhenTheQueueLists(TestCase):
	"""T7 offered "Accept the changes" and appeared in no queue.

	The bar asked whether the head had moved past the confirmed revision. The
	queue asks whether any *entry* is unconfirmed, which is a narrower and a
	better question: a prose edit -- a tag, a reference, a field added to Data
	properties -- moves the head and changes no value, so there is nothing
	about it for a reviewer to admit to search. Every table edited by hand
	since carried a button that led to an empty diff.
	"""

	def setUp(self):
		from django.contrib.auth.models import Group

		from .permissions import BOARD_GROUP

		User = get_user_model()
		self.board = User.objects.create_user('queueboard', password='x')
		group, _ = Group.objects.get_or_create(name=BOARD_GROUP)
		self.board.groups.add(group)
		self.author = User.objects.create_user('queueauthor')
		self.table = Table.objects.create(
			tid='T740', tid_int=740, url='t740', title='A published table',
			published=True, created_by=self.author)
		commit_table(self.table, self.tree({'1': '2'}),
		             author=self.author, message='m', via='orm')
		self.table.refresh_from_db()
		#Confirmed at its head, as a reviewed table is.
		self.table.reviewed_at_revision = self.table.head_revision
		self.table.save(update_fields=['reviewed_at_revision'])
		from .review import sync_review_flags

		sync_review_flags(self.table)

	def tree(self, numbers, **extra):
		document = {'Title': 'A published table',
		            'Parameters': {'n': {'type': 'Z'}},
		            'Data properties': {'type': 'Z'},
		            'Numbers': numbers}
		document.update(extra)
		return document

	def page(self):
		client = Client()
		client.force_login(self.board)
		return client.get('/T740', HTTP_HOST='numberdb.org').content.decode()

	def listed(self):
		from .review import waiting_for_review

		return 'T740' in [row['table'].tid for row in waiting_for_review()]

	def test_a_confirmed_table_offers_nothing(self):
		self.assertNotIn('Accept', self.page())
		self.assertFalse(self.listed())

	def test_a_prose_edit_alone_offers_nothing(self):
		"""The case that showed the bug: the head moves, no value changes."""
		commit_table(self.table,
		             self.tree({'1': '2'}, Tags=['statistical mechanics']),
		             author=self.author, message='a tag', via='orm')
		self.table.refresh_from_db()
		self.assertNotEqual(self.table.head_revision_id,
		                    self.table.reviewed_at_revision_id)
		self.assertFalse(self.listed())
		self.assertNotIn('Accept', self.page())

	def test_a_changed_value_offers_it(self):
		commit_table(self.table, self.tree({'1': '3'}),
		             author=self.author, message='a value', via='orm')
		self.table.refresh_from_db()
		self.assertTrue(self.listed())
		self.assertIn('Accept the changes', self.page())

	def test_the_two_never_disagree(self):
		from .review import is_waiting_for_review, waiting_for_review

		for tree, message in (
				(self.tree({'1': '2'}, Tags=['physics']), 'prose'),
				(self.tree({'1': '9'}), 'value'),
				(self.tree({'1': '9', '2': '4'}), 'another value')):
			commit_table(self.table, tree, author=self.author, message=message,
			             via='orm')
			self.table.refresh_from_db()
			with self.subTest(edit=message):
				self.assertEqual(
					is_waiting_for_review(self.table),
					'T740' in [row['table'].tid for row in waiting_for_review()])
