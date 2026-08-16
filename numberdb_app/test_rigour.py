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
			#Three columns, or four when the table needs its own sentence
			#rather than the generic one for its level.
			self.assertIn(len(parts), (3, 4), 'malformed line: %r' % (line,))
			self.assertIn(parts[1], RIGOUR_LEVELS)
			self.assertTrue(parts[2].strip(), 'no evidence given for %s' % parts[0])
			if len(parts) == 4:
				detail = parts[3].strip()
				self.assertTrue(detail, 'empty fourth column for %s' % parts[0])
				#It is shown to readers under "How they were obtained", so it
				#is prose and has to read like it.
				self.assertTrue(detail[0].isupper() and detail.endswith('.'),
				                'not a sentence for %s: %r' % (parts[0], detail))
			labelled += 1
		self.assertGreater(labelled, 50)

	def test_every_table_with_a_level_still_has_evidence(self):
		#The fifteen tables added on 2026-08-15 have no generating script, so
		#their evidence is what was done to check them here. A line with a
		#level and no evidence is a label nobody can argue with, which is the
		#thing this file exists to prevent.
		import os

		from django.conf import settings

		path = os.path.join(settings.BASE_DIR, 'docs', 'rigour-audit.tsv')
		for line in open(path, encoding='utf8'):
			if line.startswith('#') or '\t' not in line:
				continue
			tid, level, evidence = line.split('\t')[:3]
			evidence = evidence.strip()
			#`type Z` is six characters and is the whole argument for an exact
			#table: there is no precision to choose. The computed levels are
			#the ones that have to say something.
			floor = 5 if level == 'exact' else 15
			self.assertGreater(len(evidence), floor,
			                   'thin evidence for %s: %r' % (tid, evidence))


class MeasuredIsNotOnTheScale(TestCase):
	"""Four tables hold physical constants that were never computed. None of
	the five computed levels describes them, and `measured` is not a sixth
	degree of confidence -- a well-determined constant can be known to more
	digits than a heuristic computation and fewer than a proven one.
	"""

	def test_it_is_a_level(self):
		from .validate import RIGOUR_LEVELS

		self.assertIn('measured', RIGOUR_LEVELS)

	def test_but_not_one_of_the_ordered_ones(self):
		"""`weakening`, when it exists, will compare the computed levels. It
		must not be handed `measured` and asked which is better."""
		from .validate import COMPUTED_LEVELS, RIGOUR_LEVELS

		self.assertNotIn('measured', COMPUTED_LEVELS)
		self.assertEqual(set(RIGOUR_LEVELS) - set(COMPUTED_LEVELS), {'measured'})

	def test_the_api_accepts_it(self):
		from django.contrib.auth.models import User

		from .editing import create_table, tree_of
		from .models import ApiKey
		from .permissions import board_group

		user = User.objects.create_user('measurer', password='pw-123456')
		user.groups.add(board_group())
		_key, token = ApiKey.issue(user, label='k')
		table = create_table(
			{'Title': 'Measured probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=user)
		answer = self.client.post(
			'/api/table/%s/entries' % (table.tid,),
			'[{"params": {"n": "1"}, "number": "3.14159"}]',
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (token,),
			HTTP_X_RIGOUR='measured')
		self.assertEqual(answer.status_code, 200)
		table.refresh_from_db()
		self.assertEqual(tree_of(table.head_revision)['Data properties']['rigour'],
		                 'measured')

	def test_the_help_page_explains_why_it_is_different(self):
		#Whitespace-normalised, because the sentence is wrapped in the
		#template and a line break should not fail a test about wording.
		body = ' '.join(self.client.get('/help').content.decode().split())
		self.assertIn('measured', body)
		self.assertIn('not on the same scale as the others', body)

	def test_the_audit_labels_the_physical_constants(self):
		import os

		from django.conf import settings

		path = os.path.join(settings.BASE_DIR, 'docs', 'rigour-audit.tsv')
		measured = {line.split('\t')[0] for line in open(path, encoding='utf8')
		            if line.startswith('T') and '\tmeasured\t' in line}
		self.assertEqual(measured, {'T10', 'T12', 'T76', 'T78'})


class TheDetailFollowsTheLevel(TestCase):
	"""A corrected level must not leave the old explanation under it.

	T61 went out reading "proven" above "a fixed-precision value wrapped in an
	interval field, which records no error of its own" -- the sentence from the
	level it used to have. Thirteen tables said it. The command only ever added
	a detail where there was none, and skipped any table whose level already
	matched, so a level corrected upward could never have its sentence revised.
	"""

	def _table(self, properties):
		from .editing import create_table

		return create_table(
			{'Title': 'Detail test',
			 'Data properties': dict(properties),
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]})

	def _run(self, table, level, tmpdir):
		import os

		from django.core.management import call_command

		path = os.path.join(tmpdir, 'audit.tsv')
		with open(path, 'w', encoding='utf8') as handle:
			handle.write('%s\t%s\tbecause the test says so\n' % (table.tid, level))
		call_command('set_rigour', file=path, overwrite=True, verbosity=0)

		from .editing import tree_of
		table.refresh_from_db()
		return tree_of(table.head_revision)['Data properties']

	def test_a_corrected_level_takes_its_own_sentence(self):
		import tempfile

		from .management.commands.set_rigour import DETAILS

		table = self._table({'rigour': 'heuristic',
		                     'rigour details': DETAILS['heuristic']})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', tmp)

		self.assertEqual(properties['rigour'], 'proven')
		self.assertEqual(properties['rigour details'], DETAILS['proven'])
		self.assertNotIn('no error of its own', properties['rigour details'])

	def test_a_stale_sentence_is_fixed_even_when_the_level_is_right(self):
		#The exact shape of the thirteen: right label, wrong sentence. If the
		#command skips on "level already matches" this never gets repaired.
		import tempfile

		from .management.commands.set_rigour import DETAILS

		table = self._table({'rigour': 'proven',
		                     'rigour details': DETAILS['heuristic']})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', tmp)

		self.assertEqual(properties['rigour details'], DETAILS['proven'])

	def test_somebody_elses_prose_is_left_alone(self):
		import tempfile

		mine = 'Checked by hand against Gourdon and Sebah, 2003.'
		table = self._table({'rigour': 'heuristic', 'rigour details': mine})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', tmp)

		self.assertEqual(properties['rigour'], 'proven')
		self.assertEqual(properties['rigour details'], mine)

	def test_every_level_has_a_sentence(self):
		#The hole is what let a stale one survive: with no sentence for
		#`proven` there was nothing to overwrite the old one with.
		from .management.commands.set_rigour import DETAILS
		from .validate import RIGOUR_LEVELS

		self.assertEqual(set(DETAILS), set(RIGOUR_LEVELS))

	def test_no_sentence_contradicts_its_own_level(self):
		from .management.commands.set_rigour import DETAILS

		for level, detail in DETAILS.items():
			if level != 'heuristic':
				self.assertNotIn('records no error of its own', detail,
				                 '%s claims more than it does' % (level,))
			if level != 'assumed-bound':
				self.assertNotIn('asserted rather than derived', detail,
				                 '%s claims more than it does' % (level,))


class TheAuditsOwnSentencesCanBeCorrected(TestCase):
	"""A fourth-column sentence must be revisable, or it is a claim nobody
	can fix.

	The first version recognised only the generic per-level sentences as this
	command's own, so anything the audit supplied looked like hand-written
	prose and was left alone for ever. T7, T8 and T37 went on saying they had
	been checked "at 400 bits, to past the hundredth digit" after they had
	been checked at 4000 bits across all 301 and 1000 of their stored digits --
	an understatement, but the next one could as easily be the reverse.
	"""

	def _table(self, properties):
		from .editing import create_table

		return create_table(
			{'Title': 'Correctable detail test',
			 'Data properties': dict(properties),
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]})

	def _run(self, table, level, detail, tmpdir):
		import os

		from django.core.management import call_command

		path = os.path.join(tmpdir, 'audit.tsv')
		with open(path, 'w', encoding='utf8') as handle:
			handle.write('%s\t%s\tevidence enough to argue with\t%s\n'
			             % (table.tid, level, detail))
		call_command('set_rigour', file=path, overwrite=True, verbosity=0)

		from .editing import tree_of
		table.refresh_from_db()
		return tree_of(table.head_revision)['Data properties']

	def test_a_supplied_sentence_replaces_an_earlier_supplied_one(self):
		import tempfile

		first = 'Checked at 400 bits, to past the hundredth digit.'
		second = 'Checked at 4000 bits, across every stored digit.'
		table = self._table({'rigour': 'proven', 'rigour details': first})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', second, tmp)

		self.assertEqual(properties['rigour details'], second)

	def test_the_audit_wins_over_the_generic_sentence(self):
		import tempfile

		from .management.commands.set_rigour import DETAILS

		mine = 'Checked against arb certified enclosures; all 1000 agreed.'
		table = self._table({'rigour': 'proven',
		                     'rigour details': DETAILS['proven']})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', mine, tmp)

		self.assertEqual(properties['rigour details'], mine)

	def test_hand_written_prose_survives_where_the_audit_offers_none(self):
		import tempfile

		mine = 'Checked by hand against Gourdon and Sebah, 2003.'
		table = self._table({'rigour': 'heuristic', 'rigour details': mine})
		with tempfile.TemporaryDirectory() as tmp:
			properties = self._run(table, 'proven', '', tmp)

		self.assertEqual(properties['rigour details'], mine)
