"""A draft must not reach the public through its tags.

Found by giving three unpublished tables a tag no published table had:
/tags listed "continued fractions", /tags/continued+fractions listed all
three by title and T-number, and the tag API returned the same to a request
with no key at all. Everywhere else the rule holds -- a draft answers no
search, appears in no table listing, and 404s by number -- so the tag pages
were the one door left open.

The counts are part of it. `table_count` is what /tags sorts on and what
decides whether a tag is worth showing, so a count that includes drafts
announces a table nobody may look at even where no title is printed.
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase

from .editing import create_table
from .models import Tag


def document(title, tags):
	return {'Title': title,
	        'Definition': 'What these numbers are.',
	        'Tags': tags,
	        'Parameters': {'n': {'type': 'Z'}},
	        'Data properties': {'type': 'R'},
	        'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]}


class ADraftDoesNotReachThePublicThroughItsTags(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('tagger', password='pw-123456')
		self.published = create_table(
			document('A published probe', ['ring']),
			author=self.user, via='orm')
		self.draft = create_table(
			document('A secret probe', ['ring', 'secret subject']),
			author=self.user, via='orm', published=False)
		self.client = Client()

	def test_the_tag_page_lists_only_published_tables(self):
		body = self.client.get('/tags/ring').content.decode('utf8')
		self.assertIn('A published probe', body)
		self.assertNotIn('A secret probe', body)

	def test_the_tag_api_answers_only_published_tables(self):
		answer = self.client.get('/api/tag', {'url': 'ring'}).json()
		titles = [t['title'] for t in answer['tables']]
		self.assertEqual(titles, ['A published probe'])

	def test_the_counts_are_of_published_tables(self):
		tag = Tag.objects.get(name='ring')
		self.assertEqual(tag.table_count, 1)
		self.assertEqual(tag.number_count, self.published.number_count)

	def test_a_tag_only_a_draft_asked_for_is_not_listed(self):
		"""It exists as a row, so publishing the draft brings it back."""
		self.assertTrue(Tag.objects.filter(name='secret subject').exists())
		body = self.client.get('/tags').content.decode('utf8')
		self.assertNotIn('secret subject', body)

	def test_a_tag_only_a_draft_asked_for_is_not_suggested(self):
		from .search import search_metadata

		tags, _tables = search_metadata('secret subject')
		self.assertEqual([tag.name for tag in tags], [])

	def test_publishing_the_draft_brings_its_tag_back(self):
		"""Publishing is what changes the answer, and nothing else has to
		happen afterwards. Before this, a table published today was missing
		from its own tags' counts until somebody edited it again."""
		from .editing import publish_table

		publish_table(self.draft)
		self.assertEqual(Tag.objects.get(name='secret subject').table_count, 1)
		self.assertEqual(Tag.objects.get(name='ring').table_count, 2)
		body = self.client.get('/tags').content.decode('utf8')
		self.assertIn('secret subject', body)

	def test_editing_a_draft_does_not_move_its_tags_counters(self):
		"""The root cause, pinned where it happened.

		`sync_tags` counted a tag over published tables and then the number
		pipeline added the difference back for every tag of every table,
		drafts included -- two writers of the same two columns, disagreeing.
		Editing a draft is what ran the second one.
		"""
		from .editing import commit_table, tree_of

		before = Tag.objects.get(name='ring').number_count
		tree = dict(tree_of(self.draft.head_revision))
		tree['Numbers'] = [{'params': {'n': '1'}, 'number': '2.72'},
		                   {'params': {'n': '2'}, 'number': '1.41'},
		                   {'params': {'n': '3'}, 'number': '1.73'}]
		commit_table(self.draft, tree, author=self.user, message='more',
		             via='orm')
		self.assertEqual(Tag.objects.get(name='ring').number_count, before)
		self.assertEqual(Tag.objects.get(name='ring').table_count, 1)
