"""Tests for documents that are valid YAML and still not a table.

Unparseable YAML never reaches the write path: the editor and the API both
report it and nothing is stored. The interesting case is a document that parses
and then cannot be turned into numbers, because that failure used to happen
halfway through -- the revision written, the head advanced, and the number rows
still holding the previous values.

A table in that state renders one document and answers searches from another,
with the error long since reported and forgotten. Nothing about the page looks
wrong.
"""

import json

import yaml
from django.contrib.auth.models import Group, User
from django.test import TestCase

from .editing import (InvalidDocument, commit_table, create_table, tree_of)
from .models import ApiKey, Number, Table, TableRevision
from .permissions import BOARD_GROUP


class NothingIsHalfWritten(TestCase):

	def setUp(self):
		self.author = User.objects.create_user('invalid_probe')
		self.table = create_table(
			{'Title': 'Atomicity probe',
			 'Numbers': [{'params': {}, 'number': '3.14159'}]},
			author=self.author)
		self.good = self.table.head_revision

	def bad_edit(self):
		return commit_table(
			self.table,
			{'Title': 'Atomicity probe',
			 'Numbers': [{'params': {}, 'number': 'hello world'}]},
			author=self.author, base=self.table.head_revision)

	def test_a_value_that_is_not_a_number_is_refused(self):
		with self.assertRaises(InvalidDocument):
			self.bad_edit()

	def test_the_head_does_not_move(self):
		"""It did. The page then said one thing and search another."""
		with self.assertRaises(InvalidDocument):
			self.bad_edit()
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision_id, self.good.pk)

	def test_no_revision_is_left_behind(self):
		before = TableRevision.objects.filter(table=self.table).count()
		with self.assertRaises(InvalidDocument):
			self.bad_edit()
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before)

	def test_the_document_still_reads_as_it_did(self):
		with self.assertRaises(InvalidDocument):
			self.bad_edit()
		self.table.refresh_from_db()
		self.assertEqual(tree_of(self.table.head_revision)['Numbers'][0]['number'],
		                 '3.14159')

	def test_the_numbers_still_match_the_document(self):
		"""The property that was broken: page and search agreeing."""
		with self.assertRaises(InvalidDocument):
			self.bad_edit()
		self.assertEqual(
			[n.exact_text for n in Number.objects.filter(table=self.table)],
			['3.14159'])

	def test_a_misspelt_structural_key_is_refused_too(self):
		with self.assertRaises(InvalidDocument):
			commit_table(self.table,
			             {'Title': 'Atomicity probe',
			              'Numbers': [{'params': {}, 'numbr': '3.14'}]},
			             author=self.author, base=self.table.head_revision)

	def test_a_new_table_is_not_created_from_a_bad_document(self):
		before = Table.objects.count()
		with self.assertRaises(Exception):
			create_table({'Title': 'Never exists',
			              'Numbers': [{'params': {}, 'number': 'not a number'}]},
			             author=self.author)
		self.assertEqual(Table.objects.count(), before)


class TheEditorSaysWhatIsWrong(TestCase):

	def setUp(self):
		from .models import TableData

		self.user = User.objects.create_user('invalid_editor',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Message probe',
			 'Numbers': [{'params': {}, 'number': '3.14159'}]},
			author=self.user)

	def test_a_bad_value_is_reported_rather_than_crashing(self):
		"""It was a Sage parse error on an error page, which says nothing."""
		self.client.login(username='invalid_editor', password='pw-123456')
		response = self.client.post(
			'/edit/%s' % (self.table.tid,),
			{'table': yaml.dump(
				{'Title': 'Message probe',
				 'Numbers': [{'params': {}, 'number': 'hello world'}]},
				sort_keys=False),
			 'action': 'save', 'base': self.table.head_revision.digest})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'cannot be read as a number')

	def test_unparseable_yaml_never_reaches_the_write_path(self):
		self.client.login(username='invalid_editor', password='pw-123456')
		response = self.client.post(
			'/edit/%s' % (self.table.tid,),
			{'table': 'Title: [unclosed\n', 'action': 'save',
			 'base': self.table.head_revision.digest})
		self.assertContains(response, 'YAML format error')


class TheApiSaysWhatIsWrong(TestCase):

	def setUp(self):
		self.chair = User.objects.create_user('invalid_api')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.table = create_table(
			{'Title': 'API message probe',
			 'Numbers': [{'params': {}, 'number': '3.14159'}]},
			author=self.chair)
		_key, self.token = ApiKey.issue(user=self.chair, label='test')

	def post(self, path, body):
		return self.client.post(path, body, content_type='application/yaml',
		                        HTTP_AUTHORIZATION='Bearer %s' % (self.token,))

	def test_a_bad_value_is_a_400_with_a_reason(self):
		response = self.post(
			'/api/table/%s' % (self.table.tid,),
			yaml.dump({'Title': 'API message probe',
			           'Numbers': [{'params': {}, 'number': 'hello world'}]},
			          sort_keys=False))
		self.assertEqual(response.status_code, 400)
		self.assertIn('cannot be read as a number',
		              json.loads(response.content)['error'])

	def test_bad_entries_are_a_400_too(self):
		response = self.post(
			'/api/table/%s/entries' % (self.table.tid,),
			yaml.dump([{'params': {}, 'number': 'hello world'}],
			          sort_keys=False))
		self.assertEqual(response.status_code, 400)

	def test_the_table_is_untouched_afterwards(self):
		self.post('/api/table/%s' % (self.table.tid,),
		          yaml.dump({'Title': 'API message probe',
		                     'Numbers': [{'params': {}, 'number': 'nope'}]},
		                    sort_keys=False))
		self.table.refresh_from_db()
		self.assertEqual(
			tree_of(self.table.head_revision)['Numbers'][0]['number'], '3.14159')
