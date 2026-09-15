"""The review page says what the audit found.

The checks ran where the table was built -- a machine nobody reads afterwards
-- so T226 and four others arrived in the review queue holding two quantities
under one title, with the finding that says so sitting in a transcript on an
EC2 instance. Review is the last moment before a table becomes permanent, and
it is the one moment a person is already reading.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .editing import create_table
from .models import Table


class TheReviewPageShowsTheAudit(TestCase):

	def setUp(self):
		self.board = get_user_model().objects.create_user(
			'chair', password='x', is_staff=True, is_superuser=True)
		self.client.force_login(self.board)

	def draft(self, title, tree):
		create_table(dict(tree, Title=title), via='orm')
		table = Table.objects.get(title=title)
		table.published = False
		table.save(update_fields=['published'])
		return table

	def page(self, table):
		return self.client.get('/review/%s' % table.tid).content.decode()

	def test_a_finding_reaches_the_reviewer(self):
		table = self.draft('Ehrhart and h-star polynomials of something', {
			'Definition': 'These numbers, for a reason.',
			'Data properties': {'type': 'R'},
			'Parameters': {'n': {'type': 'Symbolic'},
			               'form': {'type': 'Symbolic'}},
			'Numbers': [{'params': {'n': str(n), 'form': f},
			             'number': '%d.%d' % (n, i)}
			            for n in range(1, 7)
			            for i, f in enumerate(['ehrhart', 'h-star'])]})
		body = self.page(table)
		self.assertIn('What the audit says', body)
		self.assertIn('sharing one title', body)

	def test_a_table_with_nothing_to_say_says_nothing(self):
		table = self.draft('Some quantity of something', {
			'Definition': 'A definition of these numbers, long enough to read '
			              'as a sentence and short enough to be one thing.',
			'Data properties': {'type': 'R'},
			'Parameters': {'n': {'type': 'Z'}},
			'Display properties': {'number-header': '$q(n)$'},
			'Numbers': [{'params': {'n': str(n)}, 'number': '%d.5' % n}
			            for n in range(1, 8)]})
		self.assertNotIn('What the audit says', self.page(table))
