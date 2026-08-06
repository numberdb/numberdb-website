"""Tests for editing a table's prose sections through a form.

The people this is for are mathematicians, and nothing on the page shows them
the schema -- a table's source shows what that table happens to contain, so the
way to learn that a reference may carry a DOI is to find one that does. A form
shows the shape itself, which is why it has to cover the sections and not only
the fields with fixed choices.

As with the metadata form, the property that matters is that it never destroys
what it was not shown.
"""

import json

import yaml
from django.test import SimpleTestCase, TestCase

from . import sections_form


def submitted(tree, only=None):
	"""What the form would send back if nothing were edited."""
	data = {}
	for section in sections_form.sections_from(tree):
		name = section['name']
		if only and name not in only:
			continue
		data['section.%s.present' % (name,)] = '1'
		if section['shape'] == 'text':
			data['section.%s.text' % (name,)] = section['text']
		elif section['shape'] == 'list':
			data['section.%s.items' % (name,)] = '\n'.join(section['items'])
		else:
			for index, item in enumerate(section['items']):
				data['section.%s.%d.label' % (name, index)] = item['label']
				if section['shape'] == 'labelled-text':
					data['section.%s.%d.text' % (name, index)] = item['text']
				else:
					for field, value in item['values'].items():
						data['section.%s.%d.%s' % (name, index, field)] = value
					if item.get('was_plain'):
						data['section.%s.%d.plain' % (name, index)] = '1'
					if item['extra']:
						data['section.%s.%d.extra' % (name, index)] = \
							json.dumps(item['extra'])
	return data


class ARoundTripChangesNothing(SimpleTestCase):

	TABLE = {
		'Title': 'Probe',
		'Definition': 'What these numbers are.',
		'Comments': {'comment-1': 'a remark', 'comment-2': 'another'},
		'Formulas': {'formula-1': '$a_n = n!$'},
		'References': {'Pla15': {'bib': 'David J. Platt', 'doi': '10.1090/x',
		                         'MR': '3315519'}},
		'Programs': {'program-sage': {'language': 'Sage', 'code': 'print(1)'}},
		'Links': {'Wiki': {'title': 'Wikipedia', 'url': 'https://x'}},
		'Keywords': ['analysis'],
		'Tags': ['zeta'],
		'Data properties': {'type': 'R'},
		'Numbers': [{'params': {}, 'number': '1'}],
	}

	def test_nothing_changes_when_nothing_is_edited(self):
		out = sections_form.apply_sections(self.TABLE, submitted(self.TABLE))
		self.assertEqual(out, self.TABLE)

	def test_sections_it_does_not_show_are_untouched(self):
		"""Tags, Data properties and the entries belong to other editors."""
		out = sections_form.apply_sections(self.TABLE, submitted(self.TABLE))
		self.assertEqual(out['Tags'], ['zeta'])
		self.assertEqual(out['Numbers'], self.TABLE['Numbers'])

	def test_a_section_not_submitted_at_all_is_left_alone(self):
		out = sections_form.apply_sections(
			self.TABLE, submitted(self.TABLE, only=['Definition']))
		self.assertEqual(out['Comments'], self.TABLE['Comments'])

	def test_the_order_of_sections_is_kept(self):
		out = sections_form.apply_sections(self.TABLE, submitted(self.TABLE))
		self.assertEqual(list(out), list(self.TABLE))

	def test_a_field_the_form_has_no_box_for_is_carried_through(self):
		"""`github` survived before it had a field; the next one will too."""
		tree = dict(self.TABLE)
		tree['References'] = {'X': {'bib': 'b', 'zenodo': '10.5281/x'}}
		out = sections_form.apply_sections(tree, submitted(tree))
		self.assertEqual(out['References']['X']['zenodo'], '10.5281/x')


class ReadingSections(SimpleTestCase):

	def test_definition_is_plain_text(self):
		found = sections_form.sections_from({'Definition': 'hello'})
		self.assertEqual(found[0]['text'], 'hello')

	def test_a_reference_is_read_into_its_fields(self):
		found = {s['name']: s for s in sections_form.sections_from(
			{'References': {'Pla15': {'bib': 'B', 'doi': 'd'}}})}
		item = found['References']['items'][0]
		self.assertEqual(item['label'], 'Pla15')
		self.assertEqual(item['values']['bib'], 'B')
		self.assertEqual(item['values']['doi'], 'd')

	def test_a_keywords_string_is_read_as_one_item(self):
		"""94 tables write it as a bare string and 13 as a list."""
		found = {s['name']: s for s in sections_form.sections_from(
			{'Keywords': 'analysis'})}
		self.assertEqual(found['Keywords']['items'], ['analysis'])

	def test_a_link_that_is_a_bare_string_still_shows(self):
		found = {s['name']: s for s in sections_form.sections_from(
			{'Links': {'Wiki': 'https://example.org'}})}
		self.assertEqual(found['Links']['items'][0]['values']['url'],
		                 'https://example.org')

	def test_a_section_of_an_unexpected_shape_is_flagged_not_hidden(self):
		"""Shown empty, it would be deleted on the next save."""
		found = {s['name']: s for s in sections_form.sections_from(
			{'Comments': ['not', 'a', 'mapping']})}
		self.assertTrue(found['Comments']['unshowable'])


class EditingSections(SimpleTestCase):

	def test_a_comment_can_be_added(self):
		out = sections_form.apply_sections({'Title': 'x'}, {
			'section.Comments.present': '1',
			'section.Comments.0.label': 'comment-new',
			'section.Comments.0.text': 'something to say'})
		self.assertEqual(out['Comments'], {'comment-new': 'something to say'})

	def test_a_row_dropped_from_the_submission_is_deleted(self):
		tree = {'Comments': {'a': 'one', 'b': 'two'}}
		out = sections_form.apply_sections(tree, {
			'section.Comments.present': '1',
			'section.Comments.0.label': 'a',
			'section.Comments.0.text': 'one'})
		self.assertEqual(out['Comments'], {'a': 'one'})

	def test_emptying_a_section_leaves_it_empty_not_absent(self):
		"""An absent section reads as "not available"; an empty one as "none
		yet", and the corpus writes the empty form for almost every table."""
		out = sections_form.apply_sections(
			{'Comments': {'a': 'one'}}, {'section.Comments.present': '1'})
		self.assertEqual(out['Comments'], {})

	def test_a_section_that_was_never_there_is_not_created(self):
		out = sections_form.apply_sections(
			{'Title': 'x'}, {'section.Comments.present': '1'})
		self.assertNotIn('Comments', out)

	def test_a_row_without_a_label_is_not_kept(self):
		"""It could not be cited and could not be found again."""
		out = sections_form.apply_sections({'Title': 'x'}, {
			'section.Comments.present': '1',
			'section.Comments.0.label': '',
			'section.Comments.0.text': 'orphan'})
		self.assertNotIn('Comments', out)

	def test_rows_keep_the_order_they_arrive_in(self):
		out = sections_form.apply_sections({'Title': 'x'}, {
			'section.Comments.present': '1',
			'section.Comments.0.label': 'second',
			'section.Comments.0.text': 'b',
			'section.Comments.1.label': 'first',
			'section.Comments.1.text': 'a'})
		self.assertEqual(list(out['Comments']), ['second', 'first'])

	def test_a_list_section_is_one_item_per_line(self):
		out = sections_form.apply_sections({'Title': 'x'}, {
			'section.Keywords.present': '1',
			'section.Keywords.items': 'analysis\nzeta\n\n'})
		self.assertEqual(out['Keywords'], ['analysis', 'zeta'])

	def test_a_reference_keeps_only_the_fields_that_were_filled(self):
		out = sections_form.apply_sections({'Title': 'x'}, {
			'section.References.present': '1',
			'section.References.0.label': 'X',
			'section.References.0.bib': 'a book',
			'section.References.0.doi': '',
			'section.References.0.MR': ''})
		self.assertEqual(out['References'], {'X': {'bib': 'a book'}})


class ShapesTheCorpusActuallyUses(SimpleTestCase):
	"""Every one of these was found by running the round trip over the corpus.

	The unit tests above passed throughout, because their fixture was tidy: it
	had no empty sections, no bare-string link, no list of records. All 107
	tables changed on save until each of these was handled.
	"""

	def round_trip(self, tree):
		return sections_form.apply_sections(tree, submitted(tree))

	def test_an_empty_section_stays_empty_rather_than_vanishing(self):
		"""Most tables carry every section whether or not it is filled in."""
		tree = {'Comments': {}, 'Keywords': '', 'Numbers': []}
		self.assertEqual(self.round_trip(tree), tree)

	def test_a_link_written_as_a_bare_string_stays_a_string(self):
		tree = {'Links': {'mpmath': 'https://mpmath.org/'}}
		self.assertEqual(self.round_trip(tree), tree)

	def test_filling_in_a_second_field_promotes_it_deliberately(self):
		tree = {'Links': {'mpmath': 'https://mpmath.org/'}}
		data = submitted(tree)
		data['section.Links.0.title'] = 'mpmath'
		out = sections_form.apply_sections(tree, data)
		self.assertEqual(out['Links']['mpmath'],
		                 {'title': 'mpmath', 'url': 'https://mpmath.org/'})

	def test_keywords_written_as_one_string_stay_one_string(self):
		"""94 tables do this; making them all single-item lists gains nothing."""
		tree = {'Keywords': 'analysis'}
		self.assertEqual(self.round_trip(tree), tree)

	def test_a_second_keyword_makes_it_a_list(self):
		tree = {'Keywords': 'analysis'}
		data = submitted(tree)
		data['section.Keywords.items'] = 'analysis\nzeta'
		out = sections_form.apply_sections(tree, data)
		self.assertEqual(out['Keywords'], ['analysis', 'zeta'])

	def test_a_list_of_records_is_left_completely_alone(self):
		"""Read as names it comes out empty, and saving would delete it."""
		tree = {'Similar tables': [{'relation': 'contained in',
		                            'table': 'HREF{Integers#0}[integers]'}]}
		self.assertEqual(self.round_trip(tree), tree)

	def test_and_it_says_it_cannot_show_it(self):
		found = {s['name']: s for s in sections_form.sections_from(
			{'Similar tables': [{'relation': 'contained in'}]})}
		self.assertTrue(found['Similar tables']['unshowable'])


class AgainstTheCorpus(TestCase):
	"""Opening and saving every stored table must change none of them."""

	def test_no_table_is_altered(self):
		from .models import TableData

		data = list(TableData.objects.all()[:200])
		if not data:
			self.skipTest('no tables loaded')
		for td in data:
			tree = yaml.load(td.full_yaml, Loader=yaml.BaseLoader) or {}
			out = sections_form.apply_sections(tree, submitted(tree))
			self.assertEqual(out, tree, str(td.table))


class ThroughThePage(TestCase):
	"""The sections form end to end.

	The test that matters is the same one as for the model: open the page, send
	it back untouched, and nothing should have changed. Doing it through HTML
	rather than through a dict catches what the template forgets to send.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('sections_user',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Sections probe',
			 'Definition': 'What these numbers are.',
			 'Comments': {'comment-1': 'a remark'},
			 'References': {'Pla15': {'bib': 'David J. Platt',
			                          'doi': '10.1090/x',
			                          'zenodo': '10.5281/kept'}},
			 'Links': {'mpmath': 'https://mpmath.org/'},
			 'Keywords': 'analysis',
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {}, 'number': '3.14'}]},
			author=self.user)
		self.client.login(username='sections_user', password='pw-123456')

	def url(self):
		return '/edit/%s' % (self.table.tid,)

	def head(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def form_fields(self):
		"""Everything the rendered page would submit."""
		import html
		import re

		body = self.client.get('%s?form=sections' % (self.url(),)) \
			.content.decode('utf8')
		data = {}
		#Unescaped, as a browser submits it. The carried-fields JSON is full of
		#quotes, so reading it back escaped loses exactly what it is for.
		for name, value in re.findall(
				r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', body):
			data[name] = html.unescape(value)
		for name, value in re.findall(
				r'<textarea[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>',
				body, re.S):
			data[name] = html.unescape(value)
		data.pop('csrfmiddlewaretoken', None)
		return data

	def test_the_page_shows_the_fields_of_a_reference(self):
		"""The schema is nowhere else visible."""
		body = self.client.get('%s?form=sections' % (self.url(),)) \
			.content.decode('utf8')
		for field in ('bib', 'doi', 'arXiv', 'MR'):
			self.assertIn('section.References.0.%s' % (field,), body)

	def test_posting_it_back_untouched_writes_nothing(self):
		from .models import TableRevision

		before = TableRevision.objects.filter(table=self.table).count()
		data = self.form_fields()
		data['action'] = 'save-sections'
		self.client.post(self.url(), data)
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before)

	def test_a_field_with_no_box_survives_the_page(self):
		"""`zenodo` has no field; it must come back through the hidden one."""
		data = self.form_fields()
		data['action'] = 'save-sections'
		self.client.post(self.url(), data)
		self.assertEqual(self.head()['References']['Pla15']['zenodo'],
		                 '10.5281/kept')

	def test_editing_a_comment_saves(self):
		data = self.form_fields()
		data['action'] = 'save-sections'
		data['section.Comments.0.text'] = 'a better remark'
		self.client.post(self.url(), data)
		self.assertEqual(self.head()['Comments'],
		                 {'comment-1': 'a better remark'})

	def test_adding_a_reference_saves(self):
		data = self.form_fields()
		data['action'] = 'save-sections'
		data['section.References.1.label'] = 'New24'
		data['section.References.1.bib'] = 'Somebody, 2024'
		self.client.post(self.url(), data)
		self.assertIn('New24', self.head()['References'])

	def test_removing_a_row_deletes_it(self):
		data = {k: v for k, v in self.form_fields().items()
		        if not k.startswith('section.Comments.0.')}
		data['action'] = 'save-sections'
		self.client.post(self.url(), data)
		self.assertEqual(self.head()['Comments'], {})

	def test_the_page_offers_the_labels_a_citation_can_use(self):
		body = self.client.get('%s?form=sections' % (self.url(),)) \
			.content.decode('utf8')
		self.assertIn('Pla15', body)

	def test_a_signed_out_reader_cannot_save(self):
		data = self.form_fields()
		self.client.logout()
		data['action'] = 'save-sections'
		self.client.post(self.url(), data)
		self.assertEqual(self.head()['Comments'], {'comment-1': 'a remark'})
