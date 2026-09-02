"""How an edit arrived, which is a different fact from what made it.

The same generator can be run from the package on a laptop or pasted into the
form on the site, and somebody tracing an edit wants to know which. The
activity log used to guess it from `produced_by` being non-empty, which called
an API write and a package write the same thing -- and called a session edit
'web' only because nobody had filled `produced_by` in at all.
"""

import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import ApiKey, Table, TableRevision
from .permissions import TRUSTED_GROUP


class TheChannelIsRecorded(TestCase):

	def setUp(self):
		from django.contrib.auth.models import Group

		self.person = get_user_model().objects.create_user('writer')
		self.person.groups.add(Group.objects.get_or_create(name=TRUSTED_GROUP)[0])
		_, self.token = ApiKey.issue(self.person, label='test')
		self.table = Table.objects.create(
			tid='T650', tid_int=650, url='t650', title='A table',
			published=False, created_by=self.person)
		TableRevision.objects.create(table=self.table, author=self.person,
		                             content='Title: A table\n')

	def head(self):
		self.table.refresh_from_db()
		return self.table.head_revision

	def test_an_edit_defaults_to_the_site(self):
		commit_table(self.table, {'Title': 'A table', 'Numbers': {'1': '2'}},
		             author=self.person, message='m')
		self.assertEqual(self.head().via, TableRevision.VIA_WEB)

	def test_the_package_is_distinguished_from_a_raw_api_call(self):
		document = json.dumps({'Title': 'A table', 'Numbers': {'1': '3'}})
		Client().post(
			'/api/table/T650', document, content_type='application/json',
			HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % self.token,
			HTTP_X_NUMBERDB_CLIENT='numberdb-python/0.1.6')
		self.assertEqual(self.head().via, TableRevision.VIA_PACKAGE)

	def test_a_raw_api_call_says_so(self):
		document = json.dumps({'Title': 'A table', 'Numbers': {'1': '4'}})
		Client().post(
			'/api/table/T650', document, content_type='application/json',
			HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % self.token)
		self.assertEqual(self.head().via, TableRevision.VIA_API)

	def test_a_session_edit_records_the_site_and_the_assistant(self):
		import importlib.util
		import os

		from django.conf import settings

		path = os.path.join(settings.BASE_DIR, 'agents', 'session_edit.py')
		spec = importlib.util.spec_from_file_location('session_edit2', path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		module.edit_with_person(
			self.table, {'Title': 'A table', 'Numbers': {'1': '5'}},
			self.person, 'a change', assistant='Claude')
		head = self.head()
		self.assertEqual(head.via, TableRevision.VIA_WEB)
		self.assertIn('assisted by Claude', head.produced_by)

	def test_produced_by_still_answers_the_other_question(self):
		#What made the values, as opposed to how they arrived.
		document = json.dumps({'Title': 'A table', 'Numbers': {'1': '6'}})
		Client().post(
			'/api/table/T650', document, content_type='application/json',
			HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % self.token,
			HTTP_X_NUMBERDB_CLIENT='numberdb-python/0.1.6',
			HTTP_X_PRODUCED_BY='SomeGenerator, assisted by claude')
		head = self.head()
		self.assertEqual(head.via, TableRevision.VIA_PACKAGE)
		self.assertIn('SomeGenerator', head.produced_by)
		self.assertEqual(head.assisted_by, 'claude')
