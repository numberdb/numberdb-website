"""Replacing a table's document through the API, from outside the site.

`write_table` was the one writer without `csrf_exempt`. Django's CSRF
middleware then answered every outside POST with a bare 403 before the view
ran, which the client reported as "the server refused the API key" -- and the
ordinary test client, which does not enforce CSRF, could never have shown it.
A run that had created and filled a draft with one key was refused a retitle
with the same key, on 2026-08-31, and that is how it was found.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from .models import ApiKey, Table, TableRevision
from .permissions import TRUSTED_GROUP

User = get_user_model()

DOCUMENT = 'Title: A draft\nNumbers:\n  "1": "2"\n'
RETITLED = 'Title: A draft, renamed\nNumbers:\n  "1": "2"\n'


class WritingADocumentFromOutsideTheSite(TestCase):

	def setUp(self):
		self.bot = User.objects.create_user('bot')
		self.bot.groups.add(Group.objects.get_or_create(name=TRUSTED_GROUP)[0])
		_, self.token = ApiKey.issue(self.bot, label='test')
		#Enforcing CSRF is the point: a browser-less caller has no token, and
		#the API must not need one.
		self.client = Client(enforce_csrf_checks=True)
		self.table = Table.objects.create(
			tid='T500', tid_int=500, url='t500', title='A draft',
			published=False, created_by=self.bot)
		revision = TableRevision.objects.create(
			table=self.table, author=self.bot, content=DOCUMENT)
		self.table.head_revision = revision
		self.table.save()

	def write(self, document, token=None):
		return self.client.post(
			'/api/table/%s' % self.table.tid, data=document,
			content_type='application/yaml',
			HTTP_AUTHORIZATION='Bearer %s' % (token or self.token))

	def test_a_post_with_a_key_and_no_csrf_token_is_not_forbidden(self):
		response = self.write(RETITLED)
		self.assertNotEqual(response.status_code, 403, response.content[:200])
		self.assertEqual(response.status_code, 200, response.content[:200])
		self.assertEqual(json.loads(response.content)['tid'], 'T500')
		self.table.refresh_from_db()
		self.assertEqual(self.table.title, 'A draft, renamed')

	def test_a_bad_key_is_still_refused(self):
		self.assertEqual(self.write(RETITLED, token='nonsense').status_code, 403)

	def test_it_still_needs_a_key(self):
		response = self.client.post(
			'/api/table/%s' % self.table.tid, data=RETITLED,
			content_type='application/yaml')
		self.assertEqual(response.status_code, 401)
