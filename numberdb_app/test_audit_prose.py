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


class ProseThatPointsDownThePage(TestCase):
	"""Four tables said "the formula below" about what the page draws above.

	The document is written with Comments before Formulas; the site draws
	Formulas first, whatever order the document uses, so a reader who looks
	where they are told scrolls into the Programs and back. The author
	writing YAML cannot see the order the page will use, which is why this
	is a check rather than a rule to remember.
	"""

	def setUp(self):
		self.person = get_user_model().objects.create_user('pointer')
		self.table = Table.objects.create(
			tid='T402', tid_int=402, url='t402', title='A family of numbers',
			published=True)
		TableRevision.objects.create(table=self.table, author=self.person,
		                             content='Title: A family of numbers\n')

	def complaints(self, tree):
		from .management.commands.audit_table import Command

		titles = {t.title.lower(): t for t in Table.objects.all()}
		urls = {t.url for t in Table.objects.all()}
		return list(Command()._prose_faults(self.table, tree, urls, titles))

	def pointing(self, text):
		found = self.complaints({'Title': 'A family of numbers',
		                         'Comments': {'c': text}})
		return [f for f in found if 'Formulas before Comments' in f]

	def test_the_formula_below(self):
		self.assertTrue(self.pointing(
			'so that the class number formula below turns the value into a '
			'closed form'))

	def test_the_formulas_below(self):
		self.assertTrue(self.pointing(
			'it follows from the Bernoulli-number formulas below'))

	def test_the_programs_below(self):
		self.assertTrue(self.pointing(
			'the Sage and PARI programs below give any further one'))

	def test_a_comment_above(self):
		self.assertTrue(self.pointing('as the comment above explains'))

	def test_a_value_below_a_bound_is_not_a_pointer(self):
		#"below" about a number is ordinary mathematics and must stay quiet,
		#or the check is noise on every table with an inequality in words.
		self.assertFalse(self.pointing('the values below zero are not listed'))
		self.assertFalse(self.pointing('for $x$ below the first pole'))
		self.assertFalse(self.pointing('the entries above $10^6$ are absent'))


class FormulasThatDescribeTheRun(TestCase):
	"""Seven formulas across four tables ended by saying who checked them.

	That is a fact about the build, and in a Formulas section it reads as an
	apology: "we did not prove this, we looked". `rigour details` is the
	field for how the numbers were obtained, and in every one of the seven
	it already said the same thing.
	"""

	def setUp(self):
		self.person = get_user_model().objects.create_user('checker')
		self.table = Table.objects.create(
			tid='T403', tid_int=403, url='t403', title='A family of numbers',
			published=True)
		TableRevision.objects.create(table=self.table, author=self.person,
		                             content='Title: A family of numbers\n')

	def narration(self, text):
		from .management.commands.audit_table import Command

		titles = {t.title.lower(): t for t in Table.objects.all()}
		urls = {t.url for t in Table.objects.all()}
		found = Command()._prose_faults(
			self.table, {'Title': 'A family of numbers',
			             'Formulas': {'f': text}}, urls, titles)
		return [f for f in found if 'fact about the build' in f]

	def test_checked_on_every_entry(self):
		self.assertTrue(self.narration(r'$a=b$. Checked on every entry.'))

	def test_checked_in_ball_arithmetic_on_every_rule(self):
		self.assertTrue(self.narration(
			'$a=b$. Checked in ball arithmetic on every rule here.'))

	def test_checked_here_for_every_discriminant(self):
		self.assertTrue(self.narration(
			'$a=b$. Checked here for every $D$ in the table and every prime.'))

	def test_both_were_computed_and_agree(self):
		self.assertTrue(self.narration(
			'$a=b$; both were computed for every entry and agree.'))

	def test_was_recomputed_from(self):
		self.assertTrue(self.narration(
			'$a=b$. Every weight was recomputed from the polynomials here.'))

	def test_a_formula_that_states_a_relation_is_quiet(self):
		self.assertFalse(self.narration(
			r'$\zeta_K(-1)=\frac{1}{60}\sum\sigma_1(n)$ (CITE{Siegel}).'))

	def test_saying_how_a_value_is_computed_is_quiet(self):
		#How the numbers are obtained is what `rigour details` is for, and
		#saying it there must not be flagged wherever it appears.
		self.assertFalse(self.narration(
			'each value was computed in ball arithmetic at 400 bits'))
