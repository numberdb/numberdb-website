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

		self.table = Table.objects.create(
			tid='T710', tid_int=710, url='t710', title='A draft table',
			published=False, created_by=self.author)
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
