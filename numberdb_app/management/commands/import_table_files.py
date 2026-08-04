"""Bring the data repository's loose files into the database.

85 of the 109 tables ship files the website has never shown: 82 `generate.sage`
scripts, plus `.txt`, `.new`, `.html` and three `.sobj`. They are the answer to
"where did these numbers come from", and leaving them in a git repository that
is meant to become a generated export would mean losing them the day the export
becomes one-way.

A table imported from the repository has no revision at all, so there is
nowhere to hang a file. This creates that first revision -- a genesis, holding
exactly the document the table already has -- and attaches the files to it. Its
content is produced by `dump_tree`, the same normalisation an edit uses, so the
first real edit diffs against something an editor would have written rather than
showing the whole table as changed.
"""

import hashlib
import os

import yaml
from django.core.management.base import BaseCommand

from numberdb_app.editing import commit_table, manifest_of
from numberdb_app.models import Table

#Names that are the table itself rather than something it carries. `id.yaml` is
#the identifier, which the schema keeps out of the document deliberately.
NOT_ATTACHMENTS = {'table.yaml', 'numbers.yaml', 'polynomials.yaml', 'id.yaml'}

#Big enough for every file in the corpus (the largest is 477 KB) and small
#enough that a stray archive is refused rather than loaded.
MAX_FILE_BYTES = 8 * 1024 * 1024


class Command(BaseCommand):
	help = "Attach the data repository's loose files to each table."

	def add_arguments(self, parser):
		parser.add_argument('--root', default='/numberdb-data',
		                    help='path to the numberdb-data checkout')
		parser.add_argument('--dry-run', action='store_true')
		parser.add_argument('--table', default='',
		                    help='one T-number, for trying it out')

	def handle(self, *args, **options):
		root = options['root']
		dry = options['dry_run']

		tables = Table.objects.exclude(path='').exclude(path=None)
		if options['table']:
			tables = tables.filter(tid=options['table'])

		attached = skipped = created = 0
		for table in tables.order_by('tid_int'):
			directory = os.path.join(root, table.path)
			if not os.path.isdir(directory):
				self.stderr.write('no directory for %s: %s'
				                  % (table.tid, directory))
				continue

			files = self.collect(directory)
			if not files:
				skipped += 1
				continue

			head = table.head_revision
			already = {name: hashlib.sha256(data).hexdigest()
			           for name, data in files.items()}
			if head is not None and manifest_of(head) == already:
				skipped += 1
				continue

			self.stdout.write('%-6s %2d file(s)  %s'
			                  % (table.tid, len(files),
			                     ', '.join(sorted(files)[:3])))
			if dry:
				attached += 1
				continue

			if head is None:
				#Genesis: the document as it stands, so that history starts
				#where the import did rather than at the first edit.
				tree = yaml.load(table.data.full_yaml, Loader=yaml.BaseLoader)
				commit_table(table, tree, author=None,
				             message='imported from the data repository',
				             produced_by='data-repository import',
				             files=files)
				created += 1
			else:
				commit_table(table, yaml.load(head.content,
				                              Loader=yaml.BaseLoader),
				             author=None, base=head,
				             message='attached the files from the data repository',
				             produced_by='data-repository import',
				             files=files)
			attached += 1

		self.stdout.write(self.style.SUCCESS(
			'%d table(s) given files, %d genesis revision(s), %d unchanged'
			% (attached, created, skipped)))

	def collect(self, directory):
		"""Every file under a table's directory that is not the table itself."""
		found = {}
		for base, _dirs, names in os.walk(directory):
			for name in names:
				if name in NOT_ATTACHMENTS or name.startswith('.'):
					continue
				full = os.path.join(base, name)
				relative = os.path.relpath(full, directory)
				size = os.path.getsize(full)
				if size > MAX_FILE_BYTES:
					self.stderr.write('too big, skipped: %s (%d bytes)'
					                  % (full, size))
					continue
				with open(full, 'rb') as handle:
					found[relative] = handle.read()
		return found
