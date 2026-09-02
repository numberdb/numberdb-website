"""A draft is not readable by a stranger, whichever route they take.

/preview/T133 loaded a table by number and rendered it, without the check the
table page makes -- so a private draft was readable by anybody who guessed its
number. Found by the critique stage on its first run, on a table that had
already passed verify, audit_table and two readings.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Table, TableData, TableRevision
from .permissions import board_group


class APreviewWillNotShowAStrangerADraft(TestCase):

	def setUp(self):
		self.author = get_user_model().objects.create_user('owner')
		self.draft = Table.objects.create(
			tid='T800', tid_int=800, url='t800', title='A private draft',
			published=False, created_by=self.author)
		TableRevision.objects.create(table=self.draft, author=self.author,
		                             content='Title: A private draft\n')
		TableData.objects.create(table=self.draft,
		                         raw_yaml='Title: A private draft\n',
		                         full_yaml='', json={})
		self.public = Table.objects.create(
			tid='T801', tid_int=801, url='t801', title='A published table',
			published=True, created_by=self.author)
		TableRevision.objects.create(table=self.public, author=self.author,
		                             content='Title: A published table\n')
		TableData.objects.create(table=self.public,
		                         raw_yaml='Title: A published table\n',
		                         full_yaml='', json={})

	def get(self, tid, user=None):
		client = Client()
		if user is not None:
			client.force_login(user)
		return client.get('/preview/%s' % tid, HTTP_HOST='numberdb.org')

	def test_a_stranger_is_told_it_is_not_there(self):
		#Not forbidden: that would confirm the number exists.
		self.assertEqual(self.get('T800').status_code, 404)

	def test_the_author_may_preview_their_own_draft(self):
		self.assertEqual(self.get('T800', self.author).status_code, 200)

	def test_the_board_may_preview_it(self):
		reviewer = get_user_model().objects.create_user('reviewer2')
		reviewer.groups.add(board_group())
		self.assertEqual(self.get('T800', reviewer).status_code, 200)

	def test_another_account_may_not(self):
		stranger = get_user_model().objects.create_user('stranger9')
		self.assertEqual(self.get('T800', stranger).status_code, 404)

	def test_a_published_table_previews_for_anybody(self):
		self.assertEqual(self.get('T801').status_code, 200)

	def test_an_unknown_number_is_not_found(self):
		self.assertEqual(self.get('T999').status_code, 404)
