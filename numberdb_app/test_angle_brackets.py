"""A '<' in a table's prose is mathematics, not markup.

A browser starts a tag at '<' followed directly by a letter and then eats
everything up to the next '>'. T13's comment on sums of powers contains
`\\sum_{k<m}` and has been rendering as half a sentence; T130's parameter list
showed 'argument ()' because `$1<D\\leq 1000$` swallowed the rest of it.
`$a < b$`, with a space, was always safe -- which is why a dozen tables carry
one and nobody noticed.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class MathematicsSurvivesRendering(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T700', tid_int=700, url='t700', title='A table',
			published=True)

	def page(self, tree):
		commit_table(self.table, tree, author=self.user, message='m', via='orm')
		return Client().get('/T700', HTTP_HOST='numberdb.org').content.decode()

	def test_a_comparison_without_a_space_is_not_eaten(self):
		body = self.page({
			'Title': 'A table', 'Numbers': {'1': '2'},
			'Comments': {'c': 'the sum over $k<m$ of powers'},
		})
		self.assertIn('of powers', body)
		self.assertIn('&lt;m', body)

	def test_a_constraint_with_one_is_not_eaten(self):
		#T130's case exactly.
		body = self.page({
			'Title': 'A table', 'Numbers': {'1': '2'},
			'Parameters': {'D': {'type': 'Z',
			                     'constraints': '$1<D\\leq 1000$'}},
		})
		self.assertIn('1000', body)

	def test_a_comparison_with_a_space_still_works(self):
		body = self.page({
			'Title': 'A table', 'Numbers': {'1': '2'},
			'Comments': {'c': 'listed only for $a < b$ here'},
		})
		self.assertIn('here', body)

	def test_a_citation_still_becomes_a_link(self):
		#The anchors render_text builds are added after the escaping.
		body = self.page({
			'Title': 'A table', 'Numbers': {'1': '2'},
			'Links': {'Wiki': {'url': 'https://example.com', 'title': 'W'}},
			'Comments': {'c': 'see CITE{Wiki} for $k<m$'},
		})
		self.assertIn('class="CITE"', body)
		self.assertIn('&lt;m', body)


class MarkupThisCodeWroteIsNotEscaped(TestCase):
	"""The data-properties block builds its own anchors -- the label of
	`rigour` links to the part of the help that explains it -- and escaping
	the finished string printed `<a class="HREF" ...>` at the reader."""

	def setUp(self):
		self.user = get_user_model().objects.create_user('author2')
		self.table = Table.objects.create(
			tid='T701', tid_int=701, url='t701', title='Another table',
			published=True)

	def page(self, tree):
		commit_table(self.table, tree, author=self.user, message='m', via='orm')
		return Client().get('/T701', HTTP_HOST='numberdb.org').content.decode()

	def test_the_rigour_label_is_still_a_link(self):
		body = self.page({
			'Title': 'Another table', 'Numbers': {'1': '2'},
			'Data properties': {'type': 'Q', 'rigour': 'proven'},
		})
		self.assertIn('href="/help#how-well-known"', body)
		self.assertNotIn('&lt;a class="HREF"', body)

	def test_the_author_half_is_still_escaped(self):
		#A '<' in rigour details is mathematics and must not eat the page.
		body = self.page({
			'Title': 'Another table', 'Numbers': {'1': '2'},
			'Data properties': {'type': 'Q', 'rigour': 'proven',
			                    'rigour details': 'exact for $k<m$ throughout'},
		})
		self.assertIn('&lt;m', body)
		self.assertIn('throughout', body)
