"""Tests for how well a table says its digits are known.

A hundred digits can be proven, believed on a stated assumption, checked by
agreement, or simply assumed. Twenty-nine tables in this corpus are the last of
those and nothing anywhere said so, because there was nowhere to say it. See
docs/design/rigour.md.

The level is set by the program that computed the numbers -- it is the one
thing the program knows and a reader cannot check -- and it is the only piece
of table metadata a generator may write. Everything else under Data properties
is somebody's prose.
"""

from django.test import TestCase


class WritingTheRigour(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table
		from .models import ApiKey
		from .permissions import board_group

		self.user = User.objects.create_user('rigour_writer',
		                                     password='pw-123456')
		self.user.groups.add(board_group())
		self.key, self.token = ApiKey.issue(self.user, label='generator')
		self.table = create_table(
			{'Title': 'Rigour probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

	def send(self, rigour=None, body=None):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (self.token,),
		           'content_type': 'application/json'}
		if rigour is not None:
			headers['HTTP_X_RIGOUR'] = rigour
		return self.client.post(
			'/api/table/%s/entries' % (self.table.tid,),
			body or '[{"params": {"n": "1"}, "number": "3.14159"}]',
			**headers)

	def properties(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision).get('Data properties') or {}

	def test_a_declared_level_is_recorded_on_the_table(self):
		self.send(rigour='proven')
		self.assertEqual(self.properties().get('rigour'), 'proven')

	def test_it_is_recorded_once_rather_than_on_every_entry(self):
		"""A property of the method, not of each number. A thousand copies of
		the same word is a thousand copies of the same word."""
		from .editing import tree_of

		self.send(rigour='heuristic')
		self.table.refresh_from_db()
		entries = tree_of(self.table.head_revision)['Numbers']
		self.assertFalse(any('rigour' in record for record in entries))

	def test_every_level_in_the_vocabulary_is_accepted(self):
		from .validate import RIGOUR_LEVELS

		for level in RIGOUR_LEVELS:
			with self.subTest(level=level):
				self.assertEqual(self.send(rigour=level).status_code, 200)
				self.assertEqual(self.properties().get('rigour'), level)

	def test_a_level_nobody_defined_is_refused(self):
		"""The value of the field is that the words mean the same thing on
		every table. 'pretty accurate' would end that on the first use."""
		answer = self.send(rigour='pretty accurate')
		self.assertEqual(answer.status_code, 400)
		self.assertNotIn('rigour', self.properties())

	def test_sending_none_leaves_what_was_there(self):
		"""An older client, or a run that does not say, must not silently
		erase a level somebody set."""
		self.send(rigour='proven')
		self.send()
		self.assertEqual(self.properties().get('rigour'), 'proven')

	def test_it_does_not_disturb_the_rest_of_the_document(self):
		self.send(rigour='proven')
		self.assertEqual(self.properties().get('type'), 'R')
		from .editing import tree_of
		self.table.refresh_from_db()
		self.assertEqual(tree_of(self.table.head_revision)['Title'],
		                 'Rigour probe')


class ShowingTheRigour(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('rigour_reader',
		                                     password='pw-123456')

	def table_with(self, level):
		from .editing import create_table

		return create_table(
			{'Title': 'Shown %s' % (level,),
			 'Data properties': {'type': 'R', 'rigour': level},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

	def test_the_table_page_says_how_well_the_digits_are_known(self):
		table = self.table_with('heuristic')
		body = self.client.get('/%s' % (table.tid,)).content.decode()
		self.assertIn('How well the digits are known', body)
		self.assertIn('heuristic', body)

	def test_a_table_that_says_nothing_shows_nothing(self):
		"""Most of the corpus, until somebody works out which it is. Better an
		absent line than a guessed one."""
		from .editing import create_table

		quiet = create_table(
			{'Title': 'Quiet', 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)
		body = self.client.get('/%s' % (quiet.tid,)).content.decode()
		self.assertNotIn('How well the digits are known', body)

	def test_the_word_is_not_flagged_as_a_misspelling(self):
		"""`rigour` is a known annotation now, so the validator suggests
		nothing and the editor shows no warning."""
		from .validate import KNOWN_ANNOTATIONS

		self.assertIn('rigour', KNOWN_ANNOTATIONS)


class TheLevelArrivesEvenWhenNoNumberChanges(TestCase):
	"""The gap that only a real publish revealed.

	With `restating=False` a re-run that finds every value already correct
	sends no entries at all -- and that is exactly the run whose purpose may be
	to state how well the numbers are known. The declaration cannot ride only
	with the entries. It rides with the source too, which every publish sends.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table
		from .models import ApiKey
		from .permissions import board_group

		self.user = User.objects.create_user('attacher', password='pw-123456')
		self.user.groups.add(board_group())
		self.key, self.token = ApiKey.issue(self.user, label='generator')
		self.table = create_table(
			{'Title': 'Attach probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

	def attach(self, rigour=None):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (self.token,),
		           'content_type': 'application/octet-stream'}
		if rigour is not None:
			headers['HTTP_X_RIGOUR'] = rigour
		return self.client.post(
			'/api/table/%s/file/generate.py' % (self.table.tid,),
			b'print("hello")', **headers)

	def properties(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision).get('Data properties') or {}

	def test_attaching_the_source_records_the_level(self):
		self.assertEqual(self.attach(rigour='proven').status_code, 200)
		self.assertEqual(self.properties().get('rigour'), 'proven')

	def test_an_unknown_level_is_refused_here_too(self):
		self.assertEqual(self.attach(rigour='quite good').status_code, 400)
		self.assertNotIn('rigour', self.properties())

	def test_and_the_file_still_arrives(self):
		self.attach(rigour='heuristic')
		self.table.refresh_from_db()
		names = [a.name for a in self.table.head_revision.attachments.all()]
		self.assertIn('generate.py', names)
