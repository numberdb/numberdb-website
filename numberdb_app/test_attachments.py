"""Tests for the files a table carries beside its numbers.

82 of the 109 tables have a `generate.sage`, and until now the site showed none
of them. The properties worth pinning down are that an ordinary edit does not
quietly drop them, that an old revision keeps pointing at the file it was
committed with, and that identical bytes are stored once.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .editing import (attach_files, commit_table, manifest_of, merge_manifests,
                      restore_revision)
from .models import Attachment, Blob, Table


class Blobs(TestCase):

	def test_identical_bytes_are_stored_once(self):
		"""The whole reason a 477 KB attachment can survive fifty edits."""
		first = Blob.store(b'print(1)')
		again = Blob.store(b'print(1)')
		self.assertEqual(first.pk, again.pk)
		self.assertEqual(Blob.objects.count(), 1)

	def test_different_bytes_are_different_blobs(self):
		Blob.store(b'print(1)')
		Blob.store(b'print(2)')
		self.assertEqual(Blob.objects.count(), 2)

	def test_text_comes_back_out(self):
		self.assertEqual(Blob.store('sage: 1+1').text(), 'sage: 1+1')

	def test_binary_reports_that_it_is_not_text(self):
		"""A .sobj must not be offered to a diff view."""
		self.assertIsNone(Blob.store(b'\x80\x03}q\x00.').text())

	def test_size_is_recorded(self):
		self.assertEqual(Blob.store(b'abcde').size, 5)


class AttachingBase(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T940', tid_int=940,
		                                  title='Attach probe', url='Attach940')
		self.alice = User.objects.create_user('alice_a', password='pw-123456')
		self.bob = User.objects.create_user('bob_a', password='pw-123456')

	def commit(self, tree, files=None, who=None, base=None, message=''):
		return commit_table(self.table, tree, author=who or self.alice,
		                    message=message, base=base, files=files,
		via='orm')

	def head(self):
		self.table.refresh_from_db()
		return self.table.head_revision


class FilesTravelWithRevisions(AttachingBase):

	def setUp(self):
		super().setUp()
		self.first = self.commit(
			{'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
			files={'generate.sage': 'print(pi)'}).revision

	def test_the_file_is_on_the_revision(self):
		self.assertEqual(set(manifest_of(self.first)), {'generate.sage'})

	def test_an_edit_that_ignores_files_keeps_them(self):
		"""The case that would otherwise quietly delete 82 scripts."""
		second = self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.15'}},
		                     base=self.first).revision
		self.assertEqual(set(manifest_of(second)), {'generate.sage'})

	def test_carrying_forward_shares_the_blob_rather_than_copying(self):
		self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.15'}},
		            base=self.first)
		self.assertEqual(Blob.objects.count(), 1)
		self.assertEqual(Attachment.objects.count(), 2)

	def test_an_old_revision_keeps_the_file_it_was_committed_with(self):
		"""Citing a revision must mean citing the code that produced it."""
		self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		            files={'generate.sage': 'print(4*atan(1))'},
		            base=self.first)
		old = Attachment.objects.get(revision=self.first, name='generate.sage')
		self.assertEqual(old.blob.text(), 'print(pi)')

	def test_a_file_can_be_removed(self):
		second = self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		                     files={'generate.sage': None},
		                     base=self.first).revision
		self.assertEqual(manifest_of(second), {})

	def test_changing_only_a_file_is_still_a_change(self):
		"""The document is identical; the table is not."""
		out = self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		                  files={'generate.sage': 'print(4*atan(1))'},
		                  base=self.first)
		self.assertFalse(out.unchanged)
		self.assertNotEqual(out.revision.pk, self.first.pk)

	def test_committing_the_same_file_again_changes_nothing(self):
		out = self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		                  files={'generate.sage': 'print(pi)'},
		                  base=self.first)
		self.assertTrue(out.unchanged)

	def test_a_restore_brings_back_the_code_of_that_version(self):
		self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		            files={'generate.sage': 'print(4*atan(1))'},
		            base=self.first)
		restore_revision(self.table, self.first, author=self.alice)
		blob = Attachment.objects.get(revision=self.head(),
		                              name='generate.sage').blob
		self.assertEqual(blob.text(), 'print(pi)')


class MergingManifests(TestCase):
	"""Same rules as the document merge, for the same reasons."""

	def test_disjoint_changes_both_survive(self):
		base = {'a.sage': '1', 'b.txt': '2'}
		merged, conflicts = merge_manifests(
			base, {'a.sage': '9', 'b.txt': '2'}, {'a.sage': '1', 'b.txt': '8'})
		self.assertEqual(conflicts, [])
		self.assertEqual(merged, {'a.sage': '9', 'b.txt': '8'})

	def test_the_same_change_on_both_sides_is_not_a_conflict(self):
		merged, conflicts = merge_manifests(
			{'a.sage': '1'}, {'a.sage': '9'}, {'a.sage': '9'})
		self.assertEqual(conflicts, [])
		self.assertEqual(merged, {'a.sage': '9'})

	def test_both_sides_changing_a_file_differently_conflicts(self):
		_, conflicts = merge_manifests(
			{'a.sage': '1'}, {'a.sage': '8'}, {'a.sage': '9'})
		self.assertEqual(conflicts, ['a.sage'])

	def test_deleted_here_and_changed_there_is_a_conflict(self):
		"""Never silently choose between losing a change and resurrecting a file."""
		_, conflicts = merge_manifests(
			{'a.sage': '1'}, {}, {'a.sage': '9'})
		self.assertEqual(conflicts, ['a.sage'])

	def test_added_only_on_one_side_is_taken(self):
		merged, conflicts = merge_manifests({}, {'new.sage': '1'}, {})
		self.assertEqual(conflicts, [])
		self.assertEqual(merged, {'new.sage': '1'})

	def test_the_same_addition_on_both_sides_is_not_a_conflict(self):
		merged, conflicts = merge_manifests({}, {'n.sage': '1'}, {'n.sage': '1'})
		self.assertEqual(conflicts, [])
		self.assertEqual(merged, {'n.sage': '1'})


class ConcurrentFileEdits(AttachingBase):

	def setUp(self):
		super().setUp()
		self.start = self.commit(
			{'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
			files={'generate.sage': 'print(pi)', 'notes.txt': 'hello'}).revision

	def test_two_people_touching_different_files_merge(self):
		commit_table(self.table, {'Title': 'Attach probe',
		                          'Numbers': {'1': '3.14'}},
		             author=self.bob, base=self.start,
		             files={'notes.txt': 'goodbye'},
		via='orm')
		out = commit_table(self.table, {'Title': 'Attach probe',
		                               'Numbers': {'1': '3.14'}},
		                   author=self.alice, base=self.start,
		                   files={'generate.sage': 'print(4*atan(1))'},
		via='orm')
		self.assertTrue(out.merged)
		names = {a.name: a.blob.text()
		         for a in out.revision.attachments.select_related('blob')}
		self.assertEqual(names, {'generate.sage': 'print(4*atan(1))',
		                         'notes.txt': 'goodbye'})

	def test_two_people_touching_the_same_file_is_refused(self):
		from .editing import StaleEdit

		commit_table(self.table, {'Title': 'Attach probe',
		                          'Numbers': {'1': '3.14'}},
		             author=self.bob, base=self.start,
		             files={'generate.sage': 'bob was here'},
		via='orm')
		with self.assertRaises(StaleEdit):
			commit_table(self.table, {'Title': 'Attach probe',
			                          'Numbers': {'1': '3.14'}},
			             author=self.alice, base=self.start,
			             files={'generate.sage': 'alice was here'},
		via='orm')

	def test_a_merge_keeps_the_files_of_a_document_only_edit(self):
		commit_table(self.table, {'Title': 'Attach probe',
		                          'Numbers': {'1': '9.99'}},
		             author=self.bob, base=self.start,
		via='orm')
		out = commit_table(self.table, {'Title': 'Changed',
		                                'Numbers': {'1': '3.14'}},
		                   author=self.alice, base=self.start,
		via='orm')
		self.assertTrue(out.merged)
		self.assertEqual(set(manifest_of(out.revision)),
		                 {'generate.sage', 'notes.txt'})


class WhatMayBeShownAsSource(TestCase):

	def make(self, name):
		table = Table.objects.create(tid='T941', tid_int=941, title='x', url='x941')
		revision = commit_table(table, {'Title': 'x'},
		                        files={name: b'x'},
		via='orm').revision
		return revision.attachments.get()

	def test_a_sage_script_is_source(self):
		self.assertTrue(self.make('generate.sage').is_source)

	def test_a_sobj_is_not(self):
		"""Computed binary: offer the download, never the diff."""
		self.assertFalse(self.make('curves.sobj').is_source)


class ShowingFiles(AttachingBase):

	def setUp(self):
		super().setUp()
		self.first = self.commit(
			{'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
			files={'generate.sage': 'print(pi)',
			       'curves.sobj': b'\x80\x03}q\x00.'}).revision

	def test_the_list_shows_both_files(self):
		r = self.client.get('/files/%s' % (self.table.tid,))
		self.assertEqual(r.status_code, 200)
		self.assertContains(r, 'generate.sage')
		self.assertContains(r, 'curves.sobj')

	def test_a_script_is_shown_as_text(self):
		r = self.client.get('/files/%s/generate.sage' % (self.table.tid,))
		self.assertContains(r, 'print(pi)')

	def test_binary_is_handed_over_rather_than_rendered(self):
		r = self.client.get('/files/%s/curves.sobj' % (self.table.tid,))
		self.assertEqual(r['Content-Type'], 'application/octet-stream')
		self.assertIn('attachment;', r['Content-Disposition'])

	def test_uploaded_bytes_are_never_served_as_html(self):
		"""Otherwise the site is a way to host a script on its own origin."""
		self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		            files={'evil.html': '<script>alert(1)</script>'},
		            base=self.first)
		r = self.client.get('/files/%s/evil.html' % (self.table.tid,))
		self.assertEqual(r['Content-Type'], 'application/octet-stream')
		self.assertEqual(r['X-Content-Type-Options'], 'nosniff')

	def test_an_old_revision_serves_its_own_version(self):
		self.commit({'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
		            files={'generate.sage': 'print(4*atan(1))'},
		            base=self.first)
		current = self.client.get('/files/%s/generate.sage' % (self.table.tid,))
		self.assertContains(current, '4*atan(1)')
		old = self.client.get('/files/%s/generate.sage?rev=%s'
		                      % (self.table.tid, self.first.pk))
		self.assertContains(old, 'print(pi)')

	def test_a_file_that_is_not_on_that_revision_is_a_404(self):
		r = self.client.get('/files/%s/nothing.sage' % (self.table.tid,))
		self.assertEqual(r.status_code, 404)


class AmendingKeepsItsFiles(AttachingBase):
	"""A run attaching its own source after its first submission amends.

	Without this the file was accepted and dropped: the request answered 200,
	the revision gained nothing, and the code that produced the numbers was
	simply not there.
	"""

	def setUp(self):
		super().setUp()
		self.first = commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
			author=self.alice, run='run-1',
		via='orm').revision

	def test_a_file_attached_by_an_amend_is_stored(self):
		out = commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.15'}},
			author=self.alice, base=self.first, run='run-1',
			files={'generate.py': 'print(1)'},
		via='orm')
		self.assertTrue(out.amended)
		self.assertEqual(set(manifest_of(out.revision)), {'generate.py'})

	def test_it_does_not_add_a_revision(self):
		before = self.table.revisions.count()
		commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.16'}},
			author=self.alice, base=self.first, run='run-1',
			files={'generate.py': 'print(1)'},
		via='orm')
		self.assertEqual(self.table.revisions.count(), before)

	def test_files_already_there_survive_a_later_amend(self):
		commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.17'}},
			author=self.alice, base=self.first, run='run-1',
			files={'generate.py': 'print(1)'},
		via='orm')
		self.table.refresh_from_db()
		out = commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.18'}},
			author=self.alice, base=self.table.head_revision, run='run-1',
		via='orm')
		self.assertEqual(set(manifest_of(out.revision)), {'generate.py'})


class ATableAsOneDownload(AttachingBase):
	"""The numbers and the code that produced them are one thing.

	A reader could have either -- the page, or the files one at a time -- and
	somebody checking a computation wants the whole of it rather than a list of
	links.
	"""

	def setUp(self):
		super().setUp()
		self.first = commit_table(
			self.table, {'Title': 'Attach probe', 'Numbers': {'1': '3.14'}},
			author=self.alice,
			files={'generate.py': 'print(1)', 'notes.txt': 'why'},
		via='orm').revision

	def bundle(self, **params):
		import io
		import zipfile

		response = self.client.get('/bundle/%s' % (self.table.tid,), params)
		self.assertEqual(response.status_code, 200)
		return zipfile.ZipFile(io.BytesIO(response.content))

	def test_it_holds_the_table_and_its_files(self):
		names = set(self.bundle().namelist())
		self.assertIn('%s/table.yaml' % (self.table.tid,), names)
		self.assertIn('%s/generate.py' % (self.table.tid,), names)
		self.assertIn('%s/notes.txt' % (self.table.tid,), names)

	def test_the_document_carries_its_identifier(self):
		"""A file that does not say which table it is cannot be read alone."""
		import yaml

		document = yaml.safe_load(
			self.bundle().read('%s/table.yaml' % (self.table.tid,)))
		self.assertEqual(document['ID'], self.table.tid)

	def test_it_explains_itself(self):
		note = self.bundle().read('%s/README.txt' % (self.table.tid,)).decode()
		self.assertIn(self.table.tid, note)
		self.assertIn('recorded, not run', note)

	def test_an_older_version_brings_its_own_code(self):
		"""The point: the code in the bundle produced the numbers in it."""
		commit_table(self.table, {'Title': 'Attach probe',
		                          'Numbers': {'1': '9.99'}},
		             author=self.alice, base=self.first,
		             files={'generate.py': 'print(2)'},
		via='orm')
		old = self.bundle(rev=self.first.pk)
		self.assertEqual(
			old.read('%s/generate.py' % (self.table.tid,)), b'print(1)')
		self.assertIn(b'3.14', old.read('%s/table.yaml' % (self.table.tid,)))

	def test_a_draft_is_not_downloadable_by_a_stranger(self):
		self.table.published = False
		self.table.save(update_fields=['published'])
		self.assertEqual(
			self.client.get('/bundle/%s' % (self.table.tid,)).status_code, 404)
