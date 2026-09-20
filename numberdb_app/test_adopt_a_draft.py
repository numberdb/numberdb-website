"""A build that died before filling its draft leaves it adoptable.

The failure this is about: on 2026-09-19 a worker created T342, died, and the
empty draft held the title for twenty hours. Every later attempt at that
proposal was told only "already exists", so every later attempt stopped.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .editing import create_table


class TheRefusalSaysWhatToDo(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('builder', password='x')

	def document(self, title, entries=True):
		tree = {'Title': title, 'Parameters': {'n': {'type': 'Z'}}}
		if entries:
			tree['Numbers'] = {'1': '2'}
		return tree

	def refusal(self, title):
		with self.assertRaises(ValueError) as caught:
			create_table(self.document(title), author=self.user, via='api')
		return str(caught.exception)

	def test_an_empty_draft_is_to_be_continued(self):
		create_table(self.document('A table', entries=False),
		             author=self.user, via='api', published=False)
		said = self.refusal('A table')
		self.assertIn('T1', said)
		self.assertIn('no entries yet', said)
		self.assertIn('Continue', said)

	def test_a_draft_with_entries_belongs_to_somebody_else(self):
		create_table(self.document('A table'), author=self.user, via='api',
		             published=False)
		said = self.refusal('A table')
		self.assertIn('already has entries', said)
		self.assertIn('review rather than a second copy', said)

	def test_a_published_table_answers_the_proposal(self):
		create_table(self.document('A table'), author=self.user, via='api')
		said = self.refusal('A table')
		self.assertIn('published', said)
		self.assertIn('this proposal is answered', said)
