"""Tests for adding a tag to a table through the form.

Reported: adding one tag to a table removed the tags it already had.
"""

import html
import re

from django.test import TestCase


class AddingATag(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('tagger', password='pw-123456')
		self.table = create_table(
			{'Title': 'Tag probe',
			 'Definition': 'What these numbers are.',
			 'Tags': ['ring', 'Abelian group'],
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {}, 'number': '3.14'}]},
			author=self.user,
		via='orm')
		self.client.login(username='tagger', password='pw-123456')

	def tags(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision).get('Tags')

	def rendered_fields(self):
		"""Everything the browser would submit, read off the page itself.

		Built from the page rather than written by hand, because a test that
		invents its own field names tests apply_sections and not the form --
		and apply_sections was never the broken part.
		"""
		body = self.client.get('/edit/%s?form=sections'
		                       % (self.table.tid,)).content.decode()
		data = {}

		def keep(name, value):
			#Repeated names are how a picked list is submitted, so they are
			#collected rather than overwritten -- a dict here would have hidden
			#the very bug this file is about.
			if name in data:
				if not isinstance(data[name], list):
					data[name] = [data[name]]
				data[name].append(value)
			else:
				data[name] = value

		for tag in re.findall(r'<input[^>]*>', body):
			name = re.search(r'name="([^"]*)"', tag)
			if not name or 'csrfmiddlewaretoken' in name.group(1):
				continue
			#The blank row inside <template> is not submitted by a browser.
			if 'placeholder="an existing tag' in tag:
				continue
			value = re.search(r'value="([^"]*)"', tag)
			keep(name.group(1),
			     html.unescape(value.group(1)) if value else '')
		for name, body_text in re.findall(
				r'<textarea[^>]*name="([^"]*)"[^>]*>(.*?)</textarea>',
				body, re.S):
			data[name] = html.unescape(body_text)
		return data

	def test_the_page_renders_the_tags_it_has(self):
		fields = self.rendered_fields()
		self.assertEqual(fields.get('section.Tags.item'),
		                 ['ring', 'Abelian group'])

	def test_the_tag_fields_carry_no_index_to_renumber(self):
		"""The bug: the page renumbers rows after add, move and remove, and it
		rewrote `section.Tags.items.0` into `section.Tags.0.0`. The server did
		not recognise that, so adding one tag saved the section as empty and
		removed every tag the table had. Nothing to renumber now."""
		body = self.client.get('/edit/%s?form=sections'
		                       % (self.table.tid,)).content.decode()
		self.assertNotIn('name="section.Tags.items.', body)
		self.assertIn('name="section.Tags.item"', body)

	def test_saving_without_touching_anything_keeps_them(self):
		data = self.rendered_fields()
		data['action'] = 'save-sections'
		data['message'] = 'tags'
		self.client.post('/edit/%s' % (self.table.tid,), data)
		self.assertEqual(self.tags(), ['ring', 'Abelian group'])

	def test_adding_one_keeps_the_others(self):
		"""The report: adding a tag removed the tags already there."""
		data = self.rendered_fields()
		data['section.Tags.item'] = ['ring', 'Abelian group', 'test tag']
		data['action'] = 'save-sections'
		data['message'] = 'tags'
		self.client.post('/edit/%s' % (self.table.tid,), data)
		self.assertEqual(self.tags(), ['ring', 'Abelian group', 'test tag'])

	def test_the_save_actually_produces_a_revision(self):
		before = self.table.revisions.count()
		data = self.rendered_fields()
		data['section.Tags.item'] = ['ring', 'Abelian group', 'test tag']
		data['action'] = 'save-sections'
		data['message'] = 'tags'
		self.client.post('/edit/%s' % (self.table.tid,), data)
		self.table.refresh_from_db()
		self.assertEqual(self.table.revisions.count(), before + 1)


class TagsBecomeRealTags(TestCase):
	"""A tag lives in two places: in the document, and as a Tag row joined to
	the table. Only the document was written, so a tag added on the site was in
	the table's text and in no tag list anywhere -- not on /tags, not on its own
	page, and not in the picker that offers "existing tags" to the next person.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('tag_syncer',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Tag sync probe',
			 'Tags': ['ring', 'Abelian group'],
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {}, 'number': '3.14'}]},
			author=self.user,
		via='orm')
		self.client.login(username='tag_syncer', password='pw-123456')

	def save(self, tags):
		from .editing import commit_table, tree_of

		tree = dict(tree_of(self.table.head_revision))
		tree['Tags'] = tags
		commit_table(self.table, tree, author=self.user, message='tags', via='orm')
		self.table.refresh_from_db()

	def names(self):
		return sorted(tag.name for tag in self.table.tags.all())

	def test_the_tags_of_a_new_table_exist_as_tags(self):
		self.assertEqual(self.names(), ['Abelian group', 'ring'])

	def test_an_added_tag_becomes_a_tag(self):
		self.save(['ring', 'Abelian group', 'test tag'])
		self.assertIn('test tag', self.names())

	def test_it_gets_a_row_the_tag_pages_can_find(self):
		from .models import Tag

		self.save(['ring', 'Abelian group', 'test tag'])
		tag = Tag.objects.filter(name='test tag').first()
		self.assertIsNotNone(tag)
		self.assertEqual(tag.name_lowercase, 'test tag')

	def test_a_removed_tag_leaves_the_table(self):
		self.save(['ring'])
		self.assertEqual(self.names(), ['ring'])

	def test_the_count_is_recomputed_not_incremented(self):
		"""Incrementing is right exactly once and drifts on every edit after,
		and a count that drifts is worse than none, because it is shown."""
		from .models import Tag

		self.save(['ring'])
		self.save(['ring'])
		self.save(['ring'])
		self.assertEqual(Tag.objects.get(name='ring').table_count, 1)

	def test_a_tag_dropped_by_the_last_table_falls_to_zero(self):
		from .models import Tag

		self.save(['ring'])
		self.assertEqual(Tag.objects.get(name='Abelian group').table_count, 0)

	def test_a_tag_written_as_a_bare_string_is_read(self):
		"""Read as a list of characters it would create one tag per letter."""
		self.save('number theory')
		self.assertEqual(self.names(), ['number theory'])

	def test_the_next_person_is_offered_it(self):
		"""Which is the point of tags existing rather than being free text."""
		self.save(['ring', 'test tag'])
		body = self.client.get('/edit/%s?form=sections'
		                       % (self.table.tid,)).content.decode()
		self.assertIn('test tag', body)

	def test_a_new_tag_can_be_found_by_typing_its_name(self):
		"""Only the data pipeline set the search vector, so a tag created on
		the site existed, was joined to its table, was counted -- and could not
		be found, which is most of what a tag is for."""
		from .models import Tag

		self.save(['ring', 'test tag'])
		tag = Tag.objects.get(name='test tag')
		self.assertTrue(tag.search_vector)

	def test_its_number_count_is_right(self):
		"""Shown on /tags and on the tag's own page."""
		from .models import Tag

		self.save(['ring', 'test tag'])
		self.table.refresh_from_db()
		self.assertEqual(Tag.objects.get(name='test tag').number_count,
		                 self.table.number_count)
