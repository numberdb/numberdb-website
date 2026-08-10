"""Tests for the API and edit activity logs.

Two things are being checked, and the second matters more than the first. That
the log records what it should -- and that it records nothing it should not.
A log is the easiest place to leak a credential: it is written on every
request, kept for longer than anything else, and read by more people. The API
key arrives in a header on every call, so "log the request" and "log the
credential" are one careless line apart.
"""

import json
import logging

from django.test import TestCase


class CapturedLog:
	"""Collects the JSON lines a logger emitted, as dicts."""

	def __init__(self, name):
		self.name = name
		self.records = []

	def __enter__(self):
		self.handler = logging.Handler()
		self.handler.emit = lambda record: self.records.append(
			record.getMessage())
		logger = logging.getLogger(self.name)
		logger.addHandler(self.handler)
		self._was = logger.level
		logger.setLevel(logging.INFO)
		return self

	def __exit__(self, *exc):
		logger = logging.getLogger(self.name)
		logger.removeHandler(self.handler)
		logger.setLevel(self._was)
		return False

	@property
	def lines(self):
		return [json.loads(line) for line in self.records]


class ApiRequestsAreLogged(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .models import ApiKey

		self.user = User.objects.create_user('logged_user',
		                                     password='pw-123456')
		self.key, self.token = ApiKey.issue(self.user, label='the laptop')

	def call(self, path='/api/lookup?q=3.14159', **extra):
		with CapturedLog('numberdb.api') as log:
			self.client.get(path, **extra)
		return log.lines

	def test_a_request_is_recorded(self):
		lines = self.call()
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]['event'], 'api')

	def test_it_says_what_was_asked_and_what_came_back(self):
		line = self.call()[0]
		self.assertEqual(line['method'], 'GET')
		self.assertEqual(line['path'], '/api/lookup')
		self.assertIsInstance(line['status'], int)
		self.assertIsInstance(line['ms'], int)

	def test_the_client_version_is_recorded(self):
		"""The reason this log exists: knowing which package versions are out
		there is what makes it possible to change a field on purpose."""
		line = self.call(HTTP_USER_AGENT='numberdb-python/0.1.0')[0]
		self.assertEqual(line['client'], 'numberdb-python/0.1.0')

	def test_a_keyed_call_is_attributed_to_the_key(self):
		line = self.call(HTTP_AUTHORIZATION='Bearer %s' % (self.token,))[0]
		self.assertEqual(line['actor'], 'key:%s' % (self.key.prefix,))

	def test_a_logged_in_call_is_attributed_to_the_account(self):
		self.client.login(username='logged_user', password='pw-123456')
		self.assertEqual(self.call()[0]['actor'], 'user:logged_user')

	def test_an_anonymous_call_says_so(self):
		self.assertEqual(self.call()[0]['actor'], 'anonymous')

	#-- what must never appear ------------------------------------------

	def test_the_token_is_never_written_down(self):
		"""The whole token arrives in a header on every call. A log that
		echoed the request would hand out working credentials to anyone who
		can read it -- and logs are read by more people, and kept longer,
		than anything else here."""
		with CapturedLog('numberdb.api') as log:
			self.client.get('/api/lookup?q=3.14159',
			                HTTP_AUTHORIZATION='Bearer %s' % (self.token,))
		blob = '\n'.join(log.records)
		self.assertNotIn(self.token, blob)
		self.assertNotIn(self.key.hashed_key, blob)

	def test_nor_when_it_is_sent_the_other_way(self):
		with CapturedLog('numberdb.api') as log:
			self.client.get('/api/lookup?q=3.14159',
			                HTTP_X_API_KEY=self.token)
		self.assertNotIn(self.token, '\n'.join(log.records))

	def test_nor_when_the_key_is_wrong(self):
		"""A refused key is still a secret -- most often a real key with a
		typo, or one belonging to somewhere else entirely."""
		with CapturedLog('numberdb.api') as log:
			self.client.get('/api/lookup?q=3.14159',
			                HTTP_AUTHORIZATION='Bearer not-a-real-key-9x8y7z')
		self.assertNotIn('not-a-real-key-9x8y7z', '\n'.join(log.records))

	def test_no_ip_address_is_recorded(self):
		"""nginx logs those, once, for a different purpose and a shorter
		time. Twice would be collecting the same thing twice for one use."""
		with CapturedLog('numberdb.api') as log:
			self.client.get('/api/lookup?q=3.14159', REMOTE_ADDR='198.51.100.7')
		self.assertNotIn('198.51.100.7', '\n'.join(log.records))

	def test_a_vast_user_agent_is_cut_short(self):
		"""A caller chooses this header, so its length is a disk-filling
		device unless something bounds it."""
		from .activity import USER_AGENT_LIMIT

		line = self.call(HTTP_USER_AGENT='x' * 5000)[0]
		self.assertLessEqual(len(line['client']), USER_AGENT_LIMIT)

	#-- scope ------------------------------------------------------------

	def test_ordinary_browsing_is_not_logged_here(self):
		"""This log is about the API. A line per page view would bury it and
		would record reading, which is nobody's business."""
		with CapturedLog('numberdb.api') as log:
			self.client.get('/')
			self.client.get('/tables')
		self.assertEqual(log.records, [])

	def test_a_request_that_reaches_no_view_is_still_logged(self):
		"""A 404 on a mistyped endpoint is precisely what someone writes in
		to ask about."""
		lines = self.call('/api/nonesuch')
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0]['status'], 404)


class EditsAreLogged(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		self.user = User.objects.create_user('editor_user',
		                                     password='pw-123456')

	def test_a_new_revision_is_recorded(self):
		from .editing import commit_table, create_table, tree_of

		table = create_table(
			{'Title': 'Activity probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

		tree = tree_of(table.head_revision)
		tree['Title'] = 'Activity probe, corrected'
		with CapturedLog('numberdb.edit') as log:
			commit_table(table, tree, author=self.user,
			             message='fixed the title')

		self.assertEqual(len(log.lines), 1)
		line = log.lines[0]
		self.assertEqual(line['event'], 'revision')
		self.assertEqual(line['table'], table.tid)
		self.assertEqual(line['author'], 'editor_user')
		self.assertEqual(line['message'], 'fixed the title')

	def test_a_refused_edit_is_not_recorded(self):
		"""The line is written after the transaction, so a rollback leaves no
		trace of a revision that does not exist -- which is the log you would
		trust while hunting the very problem that caused it."""
		from .editing import InvalidDocument, commit_table, create_table, tree_of

		table = create_table(
			{'Title': 'Rollback probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

		tree = tree_of(table.head_revision)
		tree['Numbers'] = [{'params': {'n': '1'}, 'number': 'not a number'}]
		with CapturedLog('numberdb.edit') as log:
			try:
				commit_table(table, tree, author=self.user, message='broken')
			except Exception:
				pass
		self.assertEqual(log.records, [])
