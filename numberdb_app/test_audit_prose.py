"""What a reader notices and no other check did.

Six faults were found by Benjamin reading rendered pages in one afternoon.
Five of them are mechanical -- a phrase, a name that should be a link, a link
sitting beside the name instead of on it -- and were simply never looked for.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Table, TableRevision


class TheAuditReadsTheProse(TestCase):

	def setUp(self):
		self.person = get_user_model().objects.create_user('reader')
		self.table = Table.objects.create(
			tid='T400', tid_int=400, url='t400', title='A family of numbers',
			published=True)
		TableRevision.objects.create(table=self.table, author=self.person,
		                             content='Title: A family of numbers\n')
		self.other = Table.objects.create(
			tid='T401', tid_int=401, url='Bernoulli_numbers',
			title='Bernoulli numbers', published=True)

	def complaints(self, tree):
		from .management.commands.audit_table import Command

		titles = {t.title.lower(): t for t in Table.objects.all()}
		urls = {t.url for t in Table.objects.all()}
		return list(Command()._prose_faults(self.table, tree, urls, titles))

	def test_it_notices_editorial(self):
		found = self.complaints({'Title': 'A family of numbers',
		                         'Comments': {'c': 'This value identifies '
		                                           'nothing on its own.'}})
		self.assertTrue(any('states a fact' in f for f in found), found)

	def test_it_notices_a_positional_reference(self):
		found = self.complaints({'Title': 'A family of numbers',
		                         'Formulas': {'f': 'The first factor is '
		                                           'tabulated elsewhere.'}})
		self.assertTrue(any('Name the symbol' in f for f in found), found)

	def test_it_notices_a_family_named_but_not_linked(self):
		found = self.complaints({'Title': 'A family of numbers',
		                         'Comments': {'c': 'These are the Bernoulli '
		                                           'numbers scaled by two.'}})
		self.assertTrue(any('does not link it' in f for f in found), found)

	def test_it_notices_a_link_beside_the_name_instead_of_on_it(self):
		found = self.complaints({
			'Title': 'A family of numbers',
			'Comments': {'c': 'the Bernoulli numbers HREF{Bernoulli_numbers}, '
			                  'which are rational'}})
		self.assertTrue(any('put the link on the name' in f for f in found),
		                found)

	def test_a_properly_linked_mention_is_quiet(self):
		found = self.complaints({
			'Title': 'A family of numbers',
			'Comments': {'c': 'the HREF{Bernoulli_numbers}[Bernoulli numbers] '
			                  'are rational'}})
		self.assertEqual(found, [])

	def test_plain_prose_is_quiet(self):
		found = self.complaints({'Title': 'A family of numbers',
		                         'Definition': 'The list contains the things.',
		                         'Comments': {'c': '$q_2=3x$ is an example.'}})
		self.assertEqual(found, [])

	def test_a_table_does_not_complain_about_its_own_name(self):
		self.table.title = 'Bernoulli numbers of the second kind'
		self.table.save()
		found = self.complaints({
			'Title': 'Bernoulli numbers of the second kind',
			'Comments': {'c': 'The Bernoulli numbers of the second kind are '
			                  'defined by a generating function.'}})
		self.assertEqual(found, [])
