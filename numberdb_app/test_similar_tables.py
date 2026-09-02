"""`Similar tables` is shown to the reader.

The section has been writable since the beginning, and six tables use it: a
related table, and a sentence saying how it is related. No branch in the view
ever built it, so all of that was stored and shown to nobody -- T128's six
pointers, including the ones to T130 and T131, were invisible on the page that
names them.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class SimilarTablesAreRendered(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T701', tid_int=701, url='t701', title='A table',
			published=True)
		self.other = Table.objects.create(
			tid='T702', tid_int=702, url='Hermite_polynomials_H',
			title='Hermite polynomials', published=True)

	def page(self, tree):
		tree = dict({'Title': 'A table', 'Numbers': {'1': '2'}}, **tree)
		commit_table(self.table, tree, author=self.user, message='m', via='orm')
		return Client().get('/T701', HTTP_HOST='numberdb.org').content.decode()

	#The page ends with an HTML comment holding the whole document, so the
	#words are on it whatever the view does. The heading is what a reader
	#sees, so the heading is what these ask about.
	HEADING = '<div class="table-section-title">Similar tables</div>'

	def test_the_section_has_a_heading(self):
		body = self.page({'Similar tables': [
			{'table': 'HREF{Hermite_polynomials_H}[Hermite polynomials]',
			 'relation': 'the nodes are its roots'}]})
		self.assertIn(self.HEADING, body)

	def test_the_named_table_becomes_a_link(self):
		body = self.page({'Similar tables': [
			{'table': 'HREF{Hermite_polynomials_H}[Hermite polynomials]',
			 'relation': 'the nodes are its roots'}]})
		self.assertIn('Hermite_polynomials_H', body)
		self.assertIn('Hermite polynomials</a>', body)

	def test_the_relation_is_shown(self):
		body = self.page({'Similar tables': [
			{'table': 'HREF{Hermite_polynomials_H}[Hermite polynomials]',
			 'relation': 'the nodes are its roots'}]})
		self.assertIn('the nodes are its roots', body)

	def test_mathematics_in_a_relation_survives(self):
		#The same escaping every other section gets: `<` here is a comparison.
		body = self.page({'Similar tables': [
			{'table': 'HREF{Hermite_polynomials_H}[H]',
			 'relation': 'shared for $n<5$ only'}]})
		self.assertIn('&lt;5', body)
		self.assertIn('only', body)

	def test_a_plain_name_without_a_relation_is_shown(self):
		#13 tables write the section as a list of names rather than records.
		body = self.page({'Similar tables': ['Bernoulli numbers']})
		self.assertIn('Bernoulli numbers', body)

	def test_a_bare_string_is_shown(self):
		#And most of the rest write it as one string.
		body = self.page({'Similar tables': 'Bernoulli numbers'})
		self.assertIn('Bernoulli numbers', body)

	def test_an_empty_section_shows_no_heading(self):
		#104 tables have nothing related to name, and an empty heading on all
		#of them would be worse than the silence it replaces.
		body = self.page({'Similar tables': ''})
		self.assertNotIn(self.HEADING, body)

	def test_a_missing_section_shows_no_heading(self):
		body = self.page({})
		self.assertNotIn(self.HEADING, body)

	def test_an_empty_record_is_skipped(self):
		body = self.page({'Similar tables': [
			{'table': '', 'relation': ''},
			{'table': 'HREF{Hermite_polynomials_H}[H]', 'relation': 'r'}]})
		self.assertIn(self.HEADING, body)
		#A record with neither half would otherwise be an empty row.
		self.assertNotIn('<div class="table-entry"></div>', body)
