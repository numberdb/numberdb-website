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


class TheWriteEndpointsKeepTheirDecorators(TestCase):
	"""A helper defined immediately above a view takes that view's decorators.

	`_apply_rigour` was inserted directly above `write_file` and silently
	collected its `@csrf_exempt` and `@rate_limited`, so every attachment came
	back as a Django CSRF page -- an HTML 403, from an endpoint that answers
	JSON, on a request that had a perfectly good API key. Publishing swallows
	attachment failures by design, so two tables published with no source and
	no rigour and said nothing about it.
	"""

	def test_write_file_is_still_exempt_from_csrf(self):
		from .api import write_file

		self.assertTrue(getattr(write_file, 'csrf_exempt', False))

	def test_and_so_are_the_other_write_endpoints(self):
		from . import api

		for name in ('write_entries', 'write_table', 'create_table',
		             'table_lease'):
			with self.subTest(endpoint=name):
				view = getattr(api, name)
				self.assertTrue(getattr(view, 'csrf_exempt', False),
				                '%s is not csrf_exempt' % (name,))

	def test_the_helper_is_not_a_view(self):
		from .api import _apply_rigour

		self.assertFalse(getattr(_apply_rigour, 'csrf_exempt', False))


class TheLevelsAreDocumented(TestCase):
	"""A feature that exists only in commit messages gets re-invented.

	These check that the vocabulary a generator must use is written down where
	somebody would look for it, and -- more usefully -- that the documented
	list and the enforced list are the same one.
	"""

	def test_the_help_page_explains_the_levels(self):
		from .validate import RIGOUR_LEVELS

		body = self.client.get('/help').content.decode()
		self.assertIn('How well are the digits known', body)
		for level in RIGOUR_LEVELS:
			with self.subTest(level=level):
				self.assertIn(level, body)

	def test_the_api_reference_documents_the_header(self):
		body = self.client.get('/api/docs').content.decode()
		self.assertIn('X-Rigour', body)

	def test_the_documented_levels_are_the_enforced_ones(self):
		"""The one that will actually catch something: a level added to the
		code and not to the page, or the reverse."""
		import re

		from .validate import RIGOUR_LEVELS

		body = self.client.get('/help').content.decode()
		section = body.split('How well are the digits known', 1)[1][:2500]
		listed = set(re.findall(r'<b>([a-z()\- ]+)</b>', section))
		self.assertEqual(listed & set(RIGOUR_LEVELS), set(RIGOUR_LEVELS),
		                 'the help page lists %s' % (sorted(listed),))


class TheAuditCommand(TestCase):
	"""`set_rigour` writes docs/rigour-audit.tsv into the tables.

	It edits 88 tables in one run, so the things worth pinning are the ones
	that would be discovered afterwards: that it does not overwrite a level a
	generator set, and that it refuses a file it cannot understand rather than
	writing something plausible.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('auditor', password='pw-123456')
		self.table = create_table(
			{'Title': 'Audit probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user)

	def audit_file(self, body):
		import tempfile

		handle = tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False)
		handle.write(body)
		handle.close()
		return handle.name

	def run_command(self, body, **options):
		from io import StringIO

		from django.core.management import call_command

		out = StringIO()
		call_command('set_rigour', file=self.audit_file(body), stdout=out,
		             **options)
		return out.getvalue()

	def properties(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision).get('Data properties') or {}

	def test_it_sets_the_level(self):
		self.run_command('%s\theuristic\ta reason\n' % (self.table.tid,))
		self.assertEqual(self.properties().get('rigour'), 'heuristic')

	def test_it_records_the_evidence_in_the_history(self):
		self.run_command('%s\theuristic\twrapped a point value\n'
		                 % (self.table.tid,))
		self.table.refresh_from_db()
		self.assertIn('wrapped a point value', self.table.head_revision.message)
		self.assertEqual(self.table.head_revision.produced_by, 'rigour-audit')

	def test_a_dry_run_writes_nothing(self):
		self.run_command('%s\theuristic\ta reason\n' % (self.table.tid,),
		                 dry_run=True)
		self.assertNotIn('rigour', self.properties())

	def test_it_does_not_overwrite_what_a_generator_said(self):
		"""Two tables were labelled by the programs that produce them, which
		know better than a file written by reading one line of each."""
		self.run_command('%s\theuristic (agreement-checked)\tthe generator\n'
		                 % (self.table.tid,))
		out = self.run_command('%s\theuristic\tthe audit\n' % (self.table.tid,))
		self.assertEqual(self.properties().get('rigour'),
		                 'heuristic (agreement-checked)')
		self.assertIn('leaving it', out)

	def test_unless_asked_to(self):
		self.run_command('%s\tproven\tfirst\n' % (self.table.tid,))
		self.run_command('%s\theuristic\tsecond\n' % (self.table.tid,),
		                 overwrite=True)
		self.assertEqual(self.properties().get('rigour'), 'heuristic')

	def test_a_level_nobody_defined_stops_the_whole_run(self):
		"""Rather than writing the 40 lines before it and failing on the 41st."""
		from django.core.management.base import CommandError

		with self.assertRaises(CommandError):
			self.run_command('%s\tquite good\ta reason\n' % (self.table.tid,))
		self.assertNotIn('rigour', self.properties())

	def test_the_heuristic_ones_get_a_line_saying_why(self):
		self.run_command('%s\theuristic\ta reason\n' % (self.table.tid,))
		self.assertIn('no error of its own',
		              self.properties().get('rigour details', ''))

	def test_the_audit_file_in_the_repository_parses(self):
		"""It is data, and data with a typo in it is a command that stops
		half way."""
		import os

		from django.conf import settings

		from .validate import RIGOUR_LEVELS

		path = os.path.join(settings.BASE_DIR, 'docs', 'rigour-audit.tsv')
		self.assertTrue(os.path.exists(path))
		labelled = 0
		for line in open(path, encoding='utf8'):
			line = line.rstrip('\n')
			if not line or line.startswith('#'):
				continue
			parts = line.split('\t')
			self.assertEqual(len(parts), 3, 'malformed line: %r' % (line,))
			self.assertIn(parts[1], RIGOUR_LEVELS)
			self.assertTrue(parts[2].strip(), 'no evidence given for %s' % parts[0])
			labelled += 1
		self.assertGreater(labelled, 50)
