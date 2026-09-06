"""The parameter column is as wide as its longest label, so labels must wrap.

Three tables built in one night index their entries by a lattice rather than
by a number -- "deltoidal trihexagonal $D(3,4,6,4)$", "body-centred cubic",
"prismatic pentagonal $D(3^3,4^2)$". The cell was `white-space: nowrap`, which
is right for `6,18/11` and wrong for a phrase: the longest name set the width
of the column, and on a wide screen the numbers get half the page, so the
digits were pushed out of it.

What makes wrapping safe is a mechanism that was already there. An identity
assembled from the parameter values is written with non-breaking spaces, so it
cannot break wherever the style says it may; a symbolic value's `display` is
the author's own text and keeps its ordinary spaces. So the two kinds of label
behave differently, and this pins that difference rather than the CSS.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class LabelsThatMayBreakAndLabelsThatMayNot(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T712', tid_int=712, url='t712', title='A table',
			published=True)

	def page(self, tree):
		commit_table(self.table, tree, author=self.user, message='m',
		             via='orm')
		return Client().get('/T712', HTTP_HOST='numberdb.org').content.decode()

	def test_a_named_value_keeps_its_spaces_and_may_wrap(self):
		body = self.page({
			'Title': 'A table',
			'Parameters': {'lattice': {'type': 'Symbolic', 'display': 'lattice',
			                           'values': {'bcc': 'body-centred cubic'}}},
			'Numbers': {'bcc': '0.5'},
		})
		self.assertIn('body-centred cubic', body)
		self.assertNotIn('body-centred&nbsp;cubic', body)

	def test_an_identity_is_still_written_unbreakable(self):
		#Three parameters on one level: the label is an identity rather than
		#prose, and breaking `1, -5, -5` across lines would read as two
		#numbers. Those are assembled with non-breaking spaces, so the style
		#may say wrapping is allowed and nothing wraps.
		body = self.page({
			'Title': 'A table',
			'Parameters': {'a2': {'type': 'Z'}, 'a1': {'type': 'Z'},
			               'a0': {'type': 'Z'}},
			'Display properties': {'group parameters': [['a2', 'a1', 'a0']]},
			'Numbers': {'1,-5,-5': '0.5'},
		})
		self.assertIn('&nbsp;', body)

	def test_the_stylesheet_lets_a_label_wrap(self):
		"""The rule that pinned the column to its longest phrase."""
		body = self.page({
			'Title': 'A table',
			'Parameters': {'lattice': {'type': 'Symbolic',
			                           'values': {'bcc': 'body-centred cubic'}}},
			'Numbers': {'bcc': '0.5'},
		})
		rule = body[body.index('div.table-param-group,'):]
		rule = rule[:rule.index('}')]
		self.assertIn('white-space: normal', rule)
