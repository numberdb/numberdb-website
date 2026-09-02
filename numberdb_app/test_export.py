"""Tests for writing the database out as the data repository.

The mirror is only worth having if it is faithful, and "faithful" has a precise
meaning here: a file the export writes, read back, must be the revision it came
from. Anything less and the repository becomes a copy that looks current and
is not, which is worse than an obviously stale one.
"""

import os
import shutil
import tempfile

import yaml
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .editing import commit_table, dump_tree, tree_of, without_managed_keys
from .models import Table


class ExportBase(TestCase):

	def setUp(self):
		self.root = tempfile.mkdtemp(prefix='numberdb-export-')
		self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
		self.author = User.objects.create_user('exporter')
		self.table = Table.objects.create(
			tid='T960', tid_int=960, title='Export probe',
			url='Export960', path='data/Probes/Export_probe')
		commit_table(self.table,
		             {'Title': 'Export probe',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': [{'params': {'n': '1'}, 'number': '3.14159'}]},
		             author=self.author,
		             files={'generate.sage': 'print(pi)',
		                    'curves.sobj': b'\x80\x03}q\x00.'},
		via='orm')
		self.table.refresh_from_db()

	def export(self, **kwargs):
		call_command('export_tables', root=self.root, **kwargs)

	def path(self, *parts):
		return os.path.join(self.root, self.table.path, *parts)


class WhatIsWritten(ExportBase):

	def test_the_table_becomes_one_file(self):
		self.export()
		self.assertTrue(os.path.exists(self.path('table.yaml')))

	def test_the_file_reads_back_as_the_revision(self):
		"""The property the mirror exists for."""
		self.export()
		with open(self.path('table.yaml')) as handle:
			tree = yaml.load(handle.read(), Loader=yaml.BaseLoader)
		self.assertEqual(dump_tree(without_managed_keys(tree)),
		                 self.table.head_revision.content)

	def test_the_identifier_is_written_even_though_it_is_not_in_the_document(self):
		"""A file that does not say which table it is cannot be read alone."""
		self.export()
		with open(self.path('table.yaml')) as handle:
			tree = yaml.load(handle.read(), Loader=yaml.BaseLoader)
		self.assertEqual(tree['ID'], 'T960')
		self.assertNotIn('ID', tree_of(self.table.head_revision))

	def test_there_are_no_macros(self):
		"""A reader should not have to resolve INPUT{} to see the numbers."""
		self.export()
		with open(self.path('table.yaml')) as handle:
			text = handle.read()
		self.assertNotIn('INPUT{', text)
		self.assertIn('3.14159', text)

	def test_attachments_come_out_byte_for_byte(self):
		self.export()
		with open(self.path('generate.sage'), 'rb') as handle:
			self.assertEqual(handle.read(), b'print(pi)')
		with open(self.path('curves.sobj'), 'rb') as handle:
			self.assertEqual(handle.read(), b'\x80\x03}q\x00.')

	def test_a_table_made_on_the_site_still_gets_a_place(self):
		"""It has no directory in the repository, having never been in it."""
		from .editing import create_table

		made = create_table({'Title': 'Born here', 'Numbers': ['1']},
		                    author=self.author,
		via='orm')
		self.export()
		self.assertTrue(os.path.exists(os.path.join(
			self.root, 'data/Uncategorised', made.url, 'table.yaml')))


class WritingAgain(ExportBase):

	def test_an_unchanged_table_is_not_rewritten(self):
		"""So the mirror's own history records edits, not export runs."""
		self.export()
		stamp = os.path.getmtime(self.path('table.yaml'))
		self.export()
		self.assertEqual(os.path.getmtime(self.path('table.yaml')), stamp)

	def test_an_edited_table_is_rewritten(self):
		self.export()
		commit_table(self.table,
		             {'Title': 'Export probe',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': [{'params': {'n': '1'}, 'number': '2.71828'}]},
		             author=self.author, base=self.table.head_revision,
		via='orm')
		self.export()
		with open(self.path('table.yaml')) as handle:
			self.assertIn('2.71828', handle.read())


class Pruning(ExportBase):

	def test_a_file_the_database_no_longer_has_is_left_alone_by_default(self):
		"""Deleting from a repository is not something to do as a side effect."""
		self.export()
		stray = self.path('numbers.yaml')
		with open(stray, 'w') as handle:
			handle.write('old: true\n')
		self.export()
		self.assertTrue(os.path.exists(stray))

	def test_prune_removes_it(self):
		self.export()
		stray = self.path('numbers.yaml')
		with open(stray, 'w') as handle:
			handle.write('old: true\n')
		self.export(prune=True)
		self.assertFalse(os.path.exists(stray))

	def test_prune_keeps_what_the_database_does_have(self):
		self.export()
		self.export(prune=True)
		self.assertTrue(os.path.exists(self.path('table.yaml')))
		self.assertTrue(os.path.exists(self.path('generate.sage')))


class DryRun(ExportBase):

	def test_nothing_is_written(self):
		self.export(dry_run=True)
		self.assertFalse(os.path.exists(self.path('table.yaml')))
