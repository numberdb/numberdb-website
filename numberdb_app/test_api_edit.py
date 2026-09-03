"""A session edit goes through the API, like every other writer.

It used to call `commit_table` from a shell on the server: past the permission
checks, past the rate limits, past the validation a key-holder meets, and
recorded as `via='orm'` because that was the truth. bmatschke has a key now.

These assert what goes over the wire. Nothing here sends a request; the point
of building the request apart from sending it is that it can be read.
"""

import os
import tempfile

import yaml
from django.test import SimpleTestCase

from agents.api_edit import (DEFAULT_ASSISTANT, MESSAGE_LIMIT, edit_request,
                             read_key)


class WhatTheRequestSays(SimpleTestCase):

	def request(self, **kwargs):
		kwargs.setdefault('tid', 'T130')
		kwargs.setdefault('tree', {'Title': 'A table', 'Numbers': {'1': '2'}})
		kwargs.setdefault('message', 'what changed and why')
		return edit_request(**kwargs)

	def test_it_posts_to_the_table(self):
		url, _headers, _body = self.request()
		self.assertEqual(url, 'https://numberdb.org/api/table/T130')

	def test_a_host_without_a_trailing_slash_problem(self):
		url, _h, _b = self.request(host='https://numberdb.org/')
		self.assertEqual(url, 'https://numberdb.org/api/table/T130')

	def test_the_body_is_the_document(self):
		_url, _headers, body = self.request()
		self.assertEqual(yaml.safe_load(body.decode('utf8')),
		                 {'Title': 'A table', 'Numbers': {'1': '2'}})

	def test_the_document_keeps_its_order(self):
		#A table's keys are in a deliberate order and sorting them would
		#rewrite every file on the first save, burying the actual change.
		tree = {'Title': 'A', 'Definition': 'd', 'Numbers': {'1': '2'}}
		_url, _headers, body = self.request(tree=tree)
		self.assertEqual(list(yaml.safe_load(body.decode('utf8'))),
		                 ['Title', 'Definition', 'Numbers'])

	def test_it_says_an_assistant_helped(self):
		_url, headers, _body = self.request(assistant='claude-opus-5')
		self.assertEqual(headers['X-Produced-By'],
		                 'assisted by claude-opus-5')

	def test_produced_by_begins_with_the_phrase_the_counter_reads(self):
		#`accepted_edit_count` looks for `assisted by`; a revision that does
		#not say it is counted as hand-typed.
		_url, headers, _body = self.request()
		self.assertTrue(headers['X-Produced-By'].startswith('assisted by'))
		self.assertIn(DEFAULT_ASSISTANT, headers['X-Produced-By'])

	def test_produced_by_fits_the_column(self):
		_url, headers, _body = self.request(assistant='x' * 400)
		self.assertLessEqual(len(headers['X-Produced-By']), 100)

	def test_the_message_fits_the_column(self):
		#Postgres refused a 336-character message once and the edit was lost.
		_url, headers, _body = self.request(message='m' * 500)
		self.assertLessEqual(len(headers['X-Edit-Message']), MESSAGE_LIMIT)

	def test_no_base_revision_unless_one_is_given(self):
		_url, headers, _body = self.request()
		self.assertNotIn('X-Base-Revision', headers)

	def test_a_base_revision_is_sent_when_given(self):
		_url, headers, _body = self.request(base='abc123')
		self.assertEqual(headers['X-Base-Revision'], 'abc123')

	def test_the_key_is_not_in_the_request_it_builds(self):
		#It is added at the moment of sending, so nothing that logs or prints
		#a built request can leak it.
		_url, headers, body = self.request()
		self.assertNotIn('Authorization', headers)


class WhereTheKeyComesFrom(SimpleTestCase):

	def written(self, text):
		handle = tempfile.NamedTemporaryFile('w', suffix='-key', delete=False,
		                                     encoding='utf8')
		handle.write(text)
		handle.close()
		self.addCleanup(os.unlink, handle.name)
		return handle.name

	def test_a_bare_token(self):
		self.assertEqual(read_key(self.written('abc123\n')), 'abc123')

	def test_a_name_equals_value_file(self):
		#The Python package reads `NUMBERDB_API_KEY=...`; both shapes live in
		#~/.config/numberdb, and reading one as the other yields a key that
		#fails authentication for a reason nobody would guess.
		self.assertEqual(
			read_key(self.written('NUMBERDB_API_KEY=abc123\n')), 'abc123')

	def test_a_quoted_value(self):
		self.assertEqual(
			read_key(self.written('NUMBERDB_API_KEY="abc123"\n')), 'abc123')

	def test_an_empty_file_is_an_error_that_names_the_path(self):
		path = self.written('   \n')
		with self.assertRaises(ValueError) as caught:
			read_key(path)
		self.assertIn(path, str(caught.exception))

	def test_a_token_with_an_equals_sign_is_not_mangled(self):
		#Base64url tokens can end in '=', and splitting on the first '=' of a
		#bare token would throw the key away.
		self.assertEqual(read_key(self.written('abc=123\n')), 'abc=123')
