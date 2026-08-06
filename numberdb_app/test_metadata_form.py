"""Tests for the metadata form.

The first class is the one that matters. A form that regenerates a document
instead of patching it deletes everything it was not taught about, and the
schema is deliberately open at the annotation level -- so a regenerating form
would silently remove exactly the extensions the format exists to permit, and
the result would look like an ordinary edit.
"""

import yaml
from django.test import SimpleTestCase, TestCase

from . import metadata_form


class ARoundTripChangesNothing(SimpleTestCase):
	"""Form in, form out, no edits: the document must be untouched."""

	def round_trip(self, tree):
		fields = metadata_form.fields_from(tree)
		data = {'title': fields['title'],
		        'data_type': fields['data_type'],
		        'complete': fields['complete'],
		        'complete_condition': fields['complete_condition'],
		        'layout': fields['layout']}
		for parameter in fields['parameters']:
			for field in ('type', 'constraints', 'display'):
				data['parameter.%s.%s' % (parameter['name'], field)] = \
					parameter[field]
		return metadata_form.apply_to(tree, data)

	def test_a_plain_document_survives(self):
		tree = {'Title': 'Probe', 'Data properties': {'type': 'R'},
		        'Numbers': [{'params': {}, 'number': '1'}]}
		self.assertEqual(self.round_trip(tree), tree)

	def test_sections_the_form_never_heard_of_survive(self):
		"""The whole reason it patches rather than regenerates."""
		tree = {'Title': 'Probe',
		        'Definition': 'Something carefully written.',
		        'Comments': {'comment-1': 'years of prose'},
		        'References': {'reference-1': 'CITE{Someone}'},
		        'Links': {'link-1': 'https://example.org'},
		        'Similar tables': ['T7'],
		        'Keywords': ['analysis'],
		        'A section invented next year': {'and': 'its contents'},
		        'Data properties': {'type': 'R', 'sources': ['CITE{X}'],
		                            'reliability': 'computed with mpmath'},
		        'Numbers': [{'params': {}, 'number': '1'}]}
		self.assertEqual(self.round_trip(tree), tree)

	def test_the_entries_are_never_touched(self):
		tree = {'Title': 'Probe',
		        'Parameters': {'n': {'type': 'Z'}},
		        'Numbers': [{'params': {'n': '1'}, 'number': '3.14',
		                     'provenance': 'measured in 1987'}]}
		self.assertEqual(self.round_trip(tree)['Numbers'], tree['Numbers'])

	def test_the_section_order_is_kept(self):
		"""Order is part of the document; reordering rewrites the whole table."""
		tree = {'Title': 'Probe', 'Definition': 'd',
		        'Data properties': {'type': 'R'}, 'Numbers': []}
		self.assertEqual(list(self.round_trip(tree)), list(tree))

	def test_it_serialises_identically(self):
		tree = yaml.safe_load(
			'Title: Probe\nDefinition: d\n'
			'Data properties:\n  type: R\n  sources:\n  - CITE{X}\n'
			'Numbers: []\n')
		before = yaml.dump(tree, sort_keys=False)
		after = yaml.dump(self.round_trip(tree), sort_keys=False)
		self.assertEqual(before, after)

	def test_the_original_is_not_mutated(self):
		tree = {'Title': 'Probe', 'Data properties': {'type': 'R'}}
		metadata_form.apply_to(tree, {'data_type': 'Z'})
		self.assertEqual(tree['Data properties']['type'], 'R')


class ReadingADocument(SimpleTestCase):

	def test_it_offers_only_the_types_that_exist(self):
		fields = metadata_form.fields_from({'Title': 'x'})
		self.assertIn('Qp', fields['data_types'])
		self.assertNotIn('Wombat', fields['data_types'])

	def test_completeness_is_split_into_answer_and_condition(self):
		"""`yes, assuming GRH` is two things welded together by a text box."""
		fields = metadata_form.fields_from(
			{'Data properties': {'complete': 'yes, assuming GRH'}})
		self.assertEqual(fields['complete'], 'yes')
		self.assertEqual(fields['complete_condition'], 'assuming GRH')

	def test_a_plain_answer_has_no_condition(self):
		fields = metadata_form.fields_from(
			{'Data properties': {'complete': 'no'}})
		self.assertEqual(fields['complete'], 'no')
		self.assertEqual(fields['complete_condition'], '')

	def test_an_answer_the_form_cannot_show_is_flagged_not_hidden(self):
		"""Silently showing blank would delete it on the next save."""
		fields = metadata_form.fields_from(
			{'Data properties': {'complete': 'partially, in places'}})
		self.assertTrue(fields['complete_is_odd'])

	def test_parameters_come_with_their_editable_properties(self):
		fields = metadata_form.fields_from(
			{'Parameters': {'n': {'type': 'Z', 'constraints': '$n>0$'}}})
		self.assertEqual(fields['parameters'][0]['name'], 'n')
		self.assertEqual(fields['parameters'][0]['constraints'], '$n>0$')


class WritingADocument(SimpleTestCase):

	def test_the_type_is_set(self):
		out = metadata_form.apply_to({'Title': 'x'}, {'data_type': 'Qp'})
		self.assertEqual(out['Data properties']['type'], 'Qp')

	def test_completeness_is_rejoined_with_its_condition(self):
		out = metadata_form.apply_to(
			{'Title': 'x'}, {'complete': 'yes',
			                 'complete_condition': 'assuming GRH'})
		self.assertEqual(out['Data properties']['complete'], 'yes, assuming GRH')

	def test_an_answer_without_a_condition_stays_bare(self):
		out = metadata_form.apply_to({'Title': 'x'}, {'complete': 'no'})
		self.assertEqual(out['Data properties']['complete'], 'no')

	def test_clearing_a_field_removes_the_key(self):
		out = metadata_form.apply_to(
			{'Title': 'x', 'Data properties': {'type': 'R'}},
			{'data_type': ''})
		self.assertNotIn('Data properties', out)

	def test_an_absent_field_is_left_alone(self):
		"""A form not showing a field must not be able to delete it."""
		out = metadata_form.apply_to(
			{'Title': 'x', 'Data properties': {'type': 'R'}}, {})
		self.assertEqual(out['Data properties']['type'], 'R')

	def test_a_parameter_property_is_written(self):
		out = metadata_form.apply_to(
			{'Parameters': {'n': {'type': 'Z'}}},
			{'parameter.n.constraints': '$n > 0$'})
		self.assertEqual(out['Parameters']['n']['constraints'], '$n > 0$')

	def test_parameter_names_are_never_changed_here(self):
		"""Renaming reassigns every identity; it is not a side effect of saving."""
		out = metadata_form.apply_to(
			{'Parameters': {'n': {'type': 'Z'}}},
			{'parameter.n.type': 'R', 'parameters': 'm'})
		self.assertEqual(list(out['Parameters']), ['n'])


class AgainstTheCorpus(TestCase):
	"""Every stored table must survive a round trip untouched."""

	def test_no_table_is_altered_by_opening_and_saving_the_form(self):
		from .models import TableData

		data = list(TableData.objects.all()[:200])
		if not data:
			self.skipTest('no tables loaded')
		for td in data:
			tree = yaml.load(td.full_yaml, Loader=yaml.BaseLoader) or {}
			fields = metadata_form.fields_from(tree)
			submitted = {'title': fields['title'],
			             'data_type': fields['data_type'],
			             'complete': fields['complete'],
			             'complete_condition': fields['complete_condition'],
			             'layout': fields['layout']}
			for parameter in fields['parameters']:
				for field in ('type', 'constraints', 'display'):
					submitted['parameter.%s.%s' % (parameter['name'], field)] \
						= parameter[field]
			self.assertEqual(metadata_form.apply_to(tree, submitted), tree,
			                 str(td.table))


class ThroughThePage(TestCase):
	"""The form end to end, including that saving through it is an ordinary edit.

	It takes the same path as the source editor -- same stale-write check, same
	limits, same schema validation, same review rules -- because those are
	properties of editing rather than of a particular form, and two copies would
	drift until they disagreed about somebody's edit.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('form_user', password='pw-123456')
		self.table = create_table(
			{'Title': 'Form probe',
			 'Definition': 'Prose the form never touches.',
			 'Data properties': {'type': 'R', 'sources': ['CITE{X}']},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14159'}]},
			author=self.user)
		self.client.login(username='form_user', password='pw-123456')

	def url(self):
		return '/edit/%s' % (self.table.tid,)

	def head(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def submit(self, **fields):
		data = {'action': 'save-metadata',
		        'base': self.table.head_revision.digest,
		        'title': 'Form probe', 'data_type': 'R', 'complete': '',
		        'complete_condition': '', 'layout': '',
		        'parameter.n.type': 'Z', 'parameter.n.constraints': '',
		        'parameter.n.display': ''}
		data.update(fields)
		return self.client.post(self.url(), data)

	def test_the_form_is_reachable(self):
		response = self.client.get('%s?form=1' % (self.url(),))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'data_type')

	def test_it_offers_only_valid_types(self):
		"""A select cannot hold `Wombat`, so that error stops existing."""
		response = self.client.get('%s?form=1' % (self.url(),))
		self.assertContains(response, '<option value="Qp"')
		self.assertNotContains(response, 'Wombat')

	def test_changing_the_type_saves(self):
		self.submit(data_type='Q')
		self.assertEqual(self.head()['Data properties']['type'], 'Q')

	def test_the_prose_it_never_shows_is_untouched(self):
		"""The property the whole module is arranged around."""
		self.submit(data_type='Q')
		head = self.head()
		self.assertEqual(head['Definition'], 'Prose the form never touches.')
		self.assertEqual(head['Data properties']['sources'], ['CITE{X}'])

	def test_the_entries_are_untouched(self):
		self.submit(data_type='Q')
		self.assertEqual(self.head()['Numbers'][0]['number'], '3.14159')

	def test_completeness_and_its_condition_are_stored_together(self):
		self.submit(complete='yes', complete_condition='assuming GRH')
		self.assertEqual(self.head()['Data properties']['complete'],
		                 'yes, assuming GRH')

	def test_a_saved_condition_is_read_back_into_two_fields(self):
		self.submit(complete='yes', complete_condition='assuming GRH')
		response = self.client.get('%s?form=1' % (self.url(),))
		self.assertContains(response, 'value="assuming GRH"')

	def test_saving_without_changes_writes_nothing(self):
		from .models import TableRevision

		before = TableRevision.objects.filter(table=self.table).count()
		self.submit()
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before)

	def test_a_stale_base_is_refused_here_too(self):
		from .editing import commit_table
		from .models import TableRevision

		stale = self.table.head_revision.digest
		commit_table(self.table,
		             {'Title': 'Form probe',
		              'Definition': 'Prose the form never touches.',
		              'Data properties': {'type': 'R', 'sources': ['CITE{X}']},
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': [{'params': {'n': '1'}, 'number': '9.99'}]},
		             author=self.user, base=self.table.head_revision)
		self.table.refresh_from_db()
		response = self.client.post(self.url(), {
			'action': 'save-metadata', 'base': stale, 'title': 'Form probe',
			'data_type': 'Q', 'parameter.n.type': 'Z'})
		self.assertEqual(response.status_code, 302)
		#The other edit survives: a form save is a merge, not an overwrite.
		self.assertEqual(self.head()['Numbers'][0]['number'], '9.99')

	def test_a_signed_out_reader_cannot_save_through_it(self):
		self.client.logout()
		response = self.submit(data_type='Q')
		self.assertIn(response.status_code, (302, 403))
		self.assertEqual(self.head()['Data properties']['type'], 'R')


class ATypeTheDatabaseCannotParse(TestCase):
	"""NumberDB was meant to be able to hold any kind of number.

	One it cannot parse is shown, linked and citable, and does not answer a
	search by its digits -- T41's four hyperreals index nothing. So the list of
	types is closed for the ones that can be searched and open, deliberately,
	beyond them.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('other_type', password='pw-123456')
		self.table = create_table(
			{'Title': 'Odd numbers indeed',
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {}, 'number': '3.14'}]},
			author=self.user)
		self.client.login(username='other_type', password='pw-123456')

	def head(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def submit(self, **fields):
		data = {'action': 'save-metadata',
		        'base': self.table.head_revision.digest,
		        'title': 'Odd numbers indeed'}
		data.update(fields)
		return self.client.post('/edit/%s' % (self.table.tid,), data)

	def test_choosing_something_else_stores_the_symbol_and_the_name(self):
		self.submit(data_type=metadata_form.OTHER, other_type='*Q',
		            other_type_name='hyperrationals')
		properties = self.head()['Data properties']
		self.assertEqual(properties['type'], '*Q')
		self.assertEqual(properties['type name'], 'hyperrationals')

	def test_a_symbol_without_a_name_is_refused(self):
		"""A symbol alone is indistinguishable from a typo."""
		from .editing import InvalidDocument
		from .validate import problems

		tree = {'Title': 'x', 'Data properties': {'type': 'Wombat'},
		        'Numbers': [{'params': {}, 'number': '1'}]}
		self.assertTrue([p for p in problems(tree) if p.fatal])

	def test_a_symbol_with_a_name_is_allowed_and_noted(self):
		tree = {'Title': 'x',
		        'Data properties': {'type': 'Wombat',
		                            'type name': 'wombat numbers'},
		        'Numbers': [{'params': {}, 'number': '1'}]}
		found = validate_problems(tree)
		self.assertEqual([p.fatal for p in found], [False])
		self.assertIn('not be found by search', str(found[0]))

	def test_going_back_to_a_searchable_type_drops_the_name(self):
		"""A stale name would describe the table as something it is not."""
		self.submit(data_type=metadata_form.OTHER, other_type='*Q',
		            other_type_name='hyperrationals')
		self.table.refresh_from_db()
		self.submit(data_type='R', base=self.table.head_revision.digest)
		properties = self.head()['Data properties']
		self.assertEqual(properties['type'], 'R')
		self.assertNotIn('type name', properties)

	def test_the_form_reads_an_other_type_back_into_its_two_fields(self):
		self.submit(data_type=metadata_form.OTHER, other_type='*Q',
		            other_type_name='hyperrationals')
		self.table.refresh_from_db()
		response = self.client.get('/edit/%s?form=1' % (self.table.tid,))
		self.assertContains(response, 'value="*Q"')
		self.assertContains(response, 'value="hyperrationals"')

	def test_the_existing_ones_are_offered(self):
		"""Read from the corpus, so a new one needs no release to appear."""
		self.submit(data_type=metadata_form.OTHER, other_type='*Q',
		            other_type_name='hyperrationals')
		offered = {row['symbol'] for row in metadata_form.known_other_types()}
		self.assertIn('*R', offered)
		self.assertIn('*Q', offered)


def validate_problems(tree):
	from .validate import problems

	return problems(tree)


class TheValuesASymbolicParameterMayTake(TestCase):
	"""A value is part of the identity of every entry using it.

	`v: b` is what makes the identity `1.629911,b`, so renaming it renumbers
	those entries and their citations resolve to different numbers. Adding one
	is safe -- it creates identities that did not exist -- which is what a table
	needs when it grows a new case.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('values_user', password='pw-123456')
		self.table = create_table(
			{'Title': 'Values probe',
			 'Parameters': {'q': {'type': 'R'},
			                'v': {'type': 'Symbolic',
			                      'values': {'a': '$a$', 'b': '$b$'}}},
			 'Numbers': [{'params': {'q': '1.5', 'v': 'a'}, 'number': '2'},
			             {'params': {'q': '1.5', 'v': 'b'}, 'number': '3'}]},
			author=self.user)
		self.client.login(username='values_user', password='pw-123456')

	def head(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def values(self):
		return self.head()['Parameters']['v']['values']

	def submit(self, **fields):
		data = {'action': 'save-metadata',
		        'base': self.table.head_revision.digest,
		        'title': 'Values probe',
		        'parameter.q.type': 'R', 'parameter.v.type': 'Symbolic',
		        'parameter.v.values.present': '1',
		        'parameter.v.values.0.key': 'a',
		        'parameter.v.values.0.was': 'a',
		        'parameter.v.values.0.display': '$a$',
		        'parameter.v.values.1.key': 'b',
		        'parameter.v.values.1.was': 'b',
		        'parameter.v.values.1.display': '$b$'}
		data.update(fields)
		return self.client.post('/edit/%s' % (self.table.tid,), data)

	def test_the_values_are_shown_in_the_form(self):
		response = self.client.get('/edit/%s?form=1' % (self.table.tid,))
		self.assertContains(response, 'parameter.v.values.0.key')
		self.assertContains(response, 'add value')

	def test_a_value_can_be_added(self):
		"""What a table needs when it grows a new case."""
		self.submit(**{'parameter.v.values.new2.key': 'c',
		               'parameter.v.values.new2.display': '$c$'})
		self.assertEqual(self.values(), {'a': '$a$', 'b': '$b$', 'c': '$c$'})

	def test_how_a_value_is_written_can_be_changed(self):
		"""The display is not the identity, so nothing is renumbered."""
		self.submit(**{'parameter.v.values.1.display': r'$\beta$'})
		self.assertEqual(self.values()['b'], r'$\beta$')

	def test_a_value_cannot_be_renamed_on_a_published_table(self):
		"""Entries would keep their old identity and the list would not match."""
		self.submit(**{'parameter.v.values.1.key': 'beta'})
		self.assertIn('b', self.values())
		self.assertNotIn('beta', self.values())

	def test_a_value_in_use_cannot_be_dropped(self):
		data = {k: v for k, v in {
			'action': 'save-metadata',
			'base': self.table.head_revision.digest,
			'title': 'Values probe',
			'parameter.v.values.present': '1',
			'parameter.v.values.0.key': 'a',
			'parameter.v.values.0.was': 'a',
			'parameter.v.values.0.display': '$a$'}.items()}
		self.client.post('/edit/%s' % (self.table.tid,), data)
		self.assertIn('b', self.values())

	def test_a_value_nobody_uses_may_be_dropped(self):
		"""A list that can only grow is a list nobody tidies."""
		self.submit(**{'parameter.v.values.new2.key': 'unused',
		               'parameter.v.values.new2.display': '$u$'})
		self.assertIn('unused', self.values())
		self.submit(base=self.head() and self.table.head_revision.digest)
		self.assertNotIn('unused', self.values())

	def test_a_draft_may_still_rename(self):
		from .editing import create_table
		from .metadata_form import apply_to

		tree = {'Parameters': {'v': {'type': 'Symbolic',
		                             'values': {'a': '$a$'}}},
		        'Numbers': [{'params': {'v': 'a'}, 'number': '1'}]}
		out = apply_to(tree, {'parameter.v.type': 'Symbolic',
		                      'parameter.v.values.present': '1',
		                      'parameter.v.values.0.key': 'alpha',
		                      'parameter.v.values.0.was': 'a',
		                      'parameter.v.values.0.display': r'$\alpha$'},
		               allow_key_changes=True)
		self.assertIn('alpha', out['Parameters']['v']['values'])


class TheSettingsPageDoesNotReadEveryTable(TestCase):
	"""Offering the types already in use took 27 seconds.

	It parsed every table's document -- the largest is a quarter of a megabyte
	and there are 107 of them -- to read two short strings that Postgres can
	extract itself. The page was unusable, and nothing about it looked wrong
	except the waiting.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('speed_user', password='pw-123456')
		for index in range(6):
			create_table(
				{'Title': 'Speed probe %d' % (index,),
				 'Data properties': {'type': 'R'},
				 'Numbers': [{'params': {}, 'number': '3.14'}]},
				author=self.user)

	def test_it_asks_the_database_rather_than_reading_documents(self):
		from django.db import connection
		from django.test.utils import CaptureQueriesContext

		from .metadata_form import known_other_types

		with CaptureQueriesContext(connection) as queries:
			known_other_types()
		#One query, whatever the corpus is. Reading the documents would be one
		#query and then a parse of every one of them.
		self.assertLessEqual(len(queries), 2)

	def test_it_still_finds_a_declared_type(self):
		from .editing import create_table
		from .metadata_form import known_other_types

		create_table({'Title': 'Odd one',
		              'Data properties': {'type': '*Q',
		                                  'type name': 'hyperrationals'},
		              'Numbers': [{'params': {}, 'number': '1'}]},
		             author=self.user)
		offered = {row['symbol']: row['name'] for row in known_other_types()}
		self.assertEqual(offered.get('*Q'), 'hyperrationals')

	def test_searchable_types_are_not_offered_as_something_else(self):
		from .metadata_form import known_other_types

		self.assertNotIn('R', {row['symbol'] for row in known_other_types()})
