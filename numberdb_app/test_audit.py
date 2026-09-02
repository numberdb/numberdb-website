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
	return create_table(document, via='orm')


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

	def test_a_tag_that_reaches_only_this_table(self):
		#Not "the tag does not exist": committing a table creates its tags, so
		#that check would fire never. What matters is the tag's reach.
		table = a_table(Tags=['a tag of ones own'])
		self.assertIn('leads nowhere', findings_for(table))

	def test_a_tag_other_tables_use_is_fine(self):
		a_table(title='First user', Tags=['shared tag'])
		a_table(title='Second user', Tags=['shared tag'])
		table = a_table(title='Third user', Tags=['shared tag'])
		self.assertNotIn('leads nowhere', findings_for(table))

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
		#Two tables share the tag, so it reaches somewhere.
		a_table(title='Also tagged', Tags=['polynomial'])
		table = a_table(
			Definition='The number three, and nothing else.',
			Tags=['polynomial'],
			Comments={'c': 'Nothing surprising here.'})
		self.assertIn('Nothing to report', findings_for(table))


class APublishedTableMayNotLinkToADraft(TestCase):
	"""A draft answers 404 to everybody, so such a link is dead on every page
	view. The check passed it before, because the draft's address does exist
	in the database -- it just is not reachable.

	Two drafts may link to each other: they become visible together.
	"""

	def setUp(self):
		from .editing import create_table, publish_table

		self.draft = create_table(
			{'Title': 'Still a draft',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1.5'}]},
			published=False,
		via='orm')
		self.published = a_table(title='Already published',
		                         Comments={'c': 'See HREF{%s}.' % self.draft.url})
		publish_table(self.published)

	def test_a_published_table_linking_to_a_draft_is_a_finding(self):
		found = findings_for(self.published)
		self.assertIn('points at a draft', found)

	def test_a_draft_linking_to_a_draft_is_not(self):
		from .editing import create_table

		other = create_table(
			{'Title': 'Another draft',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '2.5'}],
			 'Comments': {'c': 'See HREF{%s}.' % self.draft.url}},
			published=False,
		via='orm')
		self.assertNotIn('points at a draft', findings_for(other))

	def test_a_link_to_a_published_table_is_still_fine(self):
		other = a_table(title='Links to the published one',
		                Comments={'c': 'See HREF{%s}.' % self.published.url})
		found = findings_for(other)
		self.assertNotIn('points at a draft', found)
		self.assertNotIn('names no table here', found)
