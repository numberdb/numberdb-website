"""Tests for the table audit.

Every check in it is a mistake that was made, published, and found later by a
person reading the table. The tests are the mistakes.
"""

from django.test import TestCase

from .editing import create_table


def a_table(**sections):
	document = {'Title': sections.pop('title', 'Audit probe'),
	            'Data properties': {'type': 'R'},
	            'Parameters': {'n': {'type': 'Z'}},
	            'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]}
	document.update(sections)
	return create_table(document)


def findings_for(table):
	from io import StringIO

	from django.core.management import call_command

	out = StringIO()
	call_command('audit_table', table.tid, stdout=out)
	return out.getvalue()


class TheAuditFindsWhatWasMissedBefore(TestCase):

	def test_a_cite_that_names_nothing(self):
		table = a_table(Comments={'c': 'As shown in CITE{Nobody}.'})
		self.assertIn('CITE{Nobody}', findings_for(table))

	def test_a_cite_naming_a_formula_on_the_same_page_is_fine(self):
		#CITE points at a Link, a Reference, *or* a label in the same table.
		#The first version of this check called fourteen of those broken.
		table = a_table(Comments={'c': 'By CITE{formula-recurrence}.'},
		                Formulas={'formula-recurrence': '$a_n = a_{n-1}$.'})
		self.assertNotIn('CITE{formula-recurrence}', findings_for(table))

	def test_an_href_to_a_table_that_does_not_exist(self):
		#T61 said HREF{Roots_or_unity} for years. One character.
		table = a_table(Comments={'c': 'See HREF{Roots_or_unity}[them].'})
		self.assertIn('Roots_or_unity', findings_for(table))

	def test_an_href_by_number_is_fine(self):
		other = a_table(title='Linked to')
		table = a_table(title='Linking', Comments={'c': 'See HREF{%s}.' % other.tid})
		self.assertNotIn('names no table', findings_for(table))

	def test_a_link_out_to_something_the_database_holds(self):
		#The Chebyshev polynomials were cited as a Wikipedia article by a table
		#whose own database has them.
		a_table(title='Bernoulli numbers of the second kind')
		table = a_table(title='Something else', Links={
			'Wiki': {'title': 'Wikipedia: Bernoulli numbers of the second kind',
			         'url': 'https://en.wikipedia.org/wiki/Bernoulli_number'}})
		self.assertIn('prefer HREF', findings_for(table))

	def test_a_tag_no_other_table_uses(self):
		table = a_table(Tags=['a tag of ones own'])
		self.assertIn('leads nowhere', findings_for(table))

	def test_a_definition_that_has_grown_into_several_things(self):
		table = a_table(Definition='The thing is defined thus. ' + (
			'Note that some authors index it differently, and it is worth '
			'saying that the companion family is listed separately, which is '
			'why each table says which it holds, and further that the values '
			'at one are the classical numbers everybody knows about. ' * 2))
		found = findings_for(table)
		self.assertIn('Definition is', found)
		self.assertIn('reads like a comment', found)

	def test_a_definition_that_is_only_a_definition_passes(self):
		table = a_table(Definition='The Fibonacci polynomials are defined by '
		                           '$F_0 = 0$, $F_1 = 1$ and $F_n = xF_{n-1} + '
		                           'F_{n-2}$.')
		self.assertNotIn('Definition', findings_for(table))

	def test_a_programs_range_that_no_longer_matches_the_table(self):
		#The published snippet said [0..150] after the table was cut to 101.
		table = a_table(Programs={'program-sage': {
			'language': 'Sage',
			'code': 'values = {n: f(n) for n in [0..150]}'}})
		self.assertIn('goes stale', findings_for(table))

	def test_a_clean_table_reports_nothing(self):
		table = a_table(
			Definition='The number three, and nothing else.',
			Tags=['polynomial'],
			Comments={'c': 'Nothing surprising here.'})
		self.assertIn('Nothing to report', findings_for(table))
