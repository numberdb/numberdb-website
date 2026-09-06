"""How a parameter's name is set, and why a word needs a `display`.

Without one, a name is set as mathematics: `$family$` is maths italic, the
six letters spaced as a product, which is what LaTeX means by it. That is the
right default for `n` and `D`, which is nearly every parameter here.

A parameter whose name is a word says how it should look, in `display`, and
plain text there stays plain text -- T17 has done it that way since it was
written, with `display: constraint`.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class AParameterSaysHowItIsWritten(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T701', tid_int=701, url='t701', title='A table',
			published=True)

	def page(self, parameters):
		commit_table(self.table,
		             {'Title': 'A table', 'Numbers': {'1': '2'},
		              'Parameters': parameters},
		             author=self.user, message='m', via='orm')
		return Client().get('/T701', HTTP_HOST='numberdb.org').content.decode()

	def test_a_plain_display_stays_plain(self):
		"""T17's mechanism: `display: constraint`, and no dollars anywhere."""
		body = self.page({'family': {'type': 'Symbolic', 'display': 'family',
		                             'title': 'family of the lattice'}})
		self.assertIn('family', body)
		self.assertNotIn('$family$', body)

	def test_a_name_with_no_display_is_set_as_mathematics(self):
		#The default, and why a word-named parameter needs a display: this is
		#the product of six variables, not the word.
		body = self.page({'family': {'type': 'Symbolic',
		                             'title': 'family of the lattice'}})
		self.assertIn('$family$', body)

	def test_a_symbol_needs_no_display(self):
		body = self.page({'n': {'type': 'Z', 'title': 'dimension'}})
		self.assertIn('$n$', body)

	def test_a_display_may_be_mathematics_too(self):
		body = self.page({'family': {'type': 'Symbolic', 'title': 'the family',
		                             'display': '$\\mathcal{F}$'}})
		self.assertIn('\\mathcal{F}', body)
		self.assertNotIn('$family$', body)

	def test_the_display_does_not_touch_the_name(self):
		#Only the display moved. The name is what an entry address is written
		#against -- `?entry=family=Lambda` -- and what a citation resolves on.
		from .models import TableData

		self.page({'family': {'type': 'Symbolic', 'display': 'family',
		                      'title': 'the family'}})
		stored = TableData.objects.get(table=self.table).json
		self.assertIn('family', stored['Parameters'])
