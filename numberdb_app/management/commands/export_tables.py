"""Write the database out as the data repository.

The repository stopped being where tables are decided and became a mirror of
what the site holds. A mirror that is never written is just a stale copy, and
this one is now several steps behind: the database holds flat records and the
history of every table, and the repository still holds the nested form from
before the conversion, with nothing anywhere saying which is current.

Two deliberate differences from what the repository used to contain:

**No macros.** 30 tables kept their entries in a sibling `numbers.yaml`
referenced by `INPUT{numbers.yaml}`, and every table pulled its identifier from
`id.yaml` -- a file whose first line said "Do NOT edit". Splitting a document
across files was how a person kept a hand-written table manageable. Generated
files have no such problem, and a reader who has to resolve macros to see the
numbers is worse off than one who does not.

**The identifier is written out.** It is not part of the document the site
stores, because it belongs to the table rather than to the text and must never
be typed by an author. But an exported file that does not say which table it is
cannot be read on its own, so the export puts it back at the top.

Nothing is committed or pushed. What to tell the world is a decision for a
person, and a command that quietly rewrote a public repository would be exactly
the sort of thing this project is trying to stop doing.
"""

import os

import yaml
from django.core.management.base import BaseCommand

from numberdb_app.editing import dump_tree, tree_of
from numberdb_app.models import Table

#Where a table created on the site goes, having no directory in the repository.
DEFAULT_SECTION = 'data/Uncategorised'


class Command(BaseCommand):
	help = 'Write every table out as files, as the data repository holds them.'

	def add_arguments(self, parser):
		parser.add_argument('--root', required=True,
		                    help='directory to write into')
		parser.add_argument('--table', default='', help='one T-number')
		parser.add_argument('--dry-run', action='store_true')
		parser.add_argument('--prune', action='store_true',
		                    help='delete files the database no longer has')

	def handle(self, *args, **options):
		root = options['root']
		self.dry = options['dry_run']

		tables = Table.objects.exclude(head_revision=None)
		if options['table']:
			tables = tables.filter(tid=options['table'])

		written = unchanged = skipped = 0
		wrote_files = 0
		kept = set()

		for table in tables.select_related('head_revision').order_by('tid_int'):
			directory = os.path.join(root, self.path_for(table))
			document = self.document_for(table)

			target = os.path.join(directory, 'table.yaml')
			kept.add(os.path.normpath(target))
			if self.put(target, document.encode('utf8')):
				written += 1
			else:
				unchanged += 1

			for attachment in table.head_revision.attachments.select_related('blob'):
				where = os.path.join(directory, attachment.name)
				kept.add(os.path.normpath(where))
				if self.put(where, bytes(attachment.blob.content)):
					wrote_files += 1

		removed = self.prune(root, kept) if options['prune'] else 0

		self.stdout.write(self.style.SUCCESS(
			'%d table(s) written, %d unchanged, %d attachment(s) written, '
			'%d file(s) removed%s'
			% (written, unchanged, wrote_files, removed,
			   ' (dry run)' if self.dry else '')))
		if not self.dry and not options['prune']:
			self.stdout.write(
				'Files the database no longer has were left alone; --prune '
				'removes them.')

	def path_for(self, table):
		"""Where this table's directory goes.

		Its existing path when it has one, so the repository's arrangement by
		subject survives. A table created on the site has none, and inventing a
		subject for it from its tags would be a guess that later has to be
		undone; a plain holding area is easier to correct.
		"""
		if table.path:
			return table.path
		return os.path.join(DEFAULT_SECTION, table.url or table.tid)

	def document_for(self, table):
		"""The table as a single self-contained file."""
		tree = tree_of(table.head_revision)
		#Identifier first, both because a reader wants it first and because it
		#is the one line an editor must not change.
		out = {'ID': table.tid}
		out.update({k: v for k, v in tree.items() if k != 'ID'})
		return dump_tree(out)

	def put(self, path, content):
		"""Write a file if its content would change. Returns whether it did."""
		if os.path.exists(path):
			with open(path, 'rb') as handle:
				if handle.read() == content:
					return False
		if self.dry:
			self.stdout.write('  would write %s' % (path,))
			return True
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, 'wb') as handle:
			handle.write(content)
		return True

	def prune(self, root, kept):
		"""Remove files under root that the database no longer accounts for.

		Only inside directories the export writes to, and never the repository's
		own machinery: a mirror should not decide that README.md is obsolete.
		"""
		removed = 0
		for base, dirs, names in os.walk(os.path.join(root, 'data')):
			dirs[:] = [d for d in dirs if d != '.git']
			for name in names:
				full = os.path.normpath(os.path.join(base, name))
				if full in kept:
					continue
				if self.dry:
					self.stdout.write('  would remove %s' % (full,))
				else:
					os.remove(full)
				removed += 1
		return removed
