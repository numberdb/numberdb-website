"""An edit made in a session says so.

Two accounts write here. zeta3 means nobody watched; a person's account means
somebody chose. Either one claiming the other's work hides something a reader
needs: that nobody read it, or that somebody did.
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from .editing import tree_of
from .models import Table, TableRevision


def helper():
    import importlib.util

    path = os.path.join(settings.BASE_DIR, 'agents', 'session_edit.py')
    spec = importlib.util.spec_from_file_location('session_edit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnEditMadeWithAPersonRecordsTheAssistant(TestCase):

	def setUp(self):
		self.person = get_user_model().objects.create_user('person9')
		self.table = Table.objects.create(
			tid='T600', tid_int=600, url='t600', title='A table',
			published=False, created_by=self.person)
		TableRevision.objects.create(table=self.table, author=self.person,
		                             content='Title: A table\n')

	def test_the_revision_says_an_assistant_helped(self):
		helper().edit_with_person(
			self.table, {'Title': 'A table', 'Numbers': {'1': '2'}},
			self.person, 'a change', assistant='Claude (Opus 5)')
		self.table.refresh_from_db()
		self.assertIn('assisted by Claude',
		              self.table.head_revision.produced_by)

	def test_it_is_not_recorded_as_typed_into_the_browser(self):
		helper().edit_with_person(
			self.table, {'Title': 'A table', 'Numbers': {'1': '4'}},
			self.person, 'a change')
		self.table.refresh_from_db()
		self.assertNotEqual(self.table.head_revision.via, 'web')

	def test_the_author_is_the_person_not_the_assistant(self):
		helper().edit_with_person(
			self.table, {'Title': 'A table', 'Numbers': {'1': '3'}},
			self.person, 'a change')
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision.author, self.person)

	def test_the_phrase_the_trust_counter_reads_is_present(self):
		from .permissions import ASSISTED_MARKER

		self.assertTrue(helper().producer('Claude').startswith(ASSISTED_MARKER))

	def test_it_says_something_even_when_the_assistant_is_unnamed(self):
		self.assertIn('assisted by', helper().producer())

	def test_it_fits_the_column(self):
		self.assertLessEqual(len(helper().producer('x' * 300)), 100)
