"""Rebuild each table's history from the data repository's git log.

Until now every table claimed to have sprung into existence on the day it was
imported, authored by nobody. For a table Alex J Best touched in March 2021
that is not a gap in the history, it is a false statement, sitting on the very
page whose job is to say who did what.

The repository holds 382 commits by four authors between 2021 and 2026, and
about 268 distinct versions of the 109 tables survive in a form that still
loads. Those become real revisions: dated when they were written, credited to
whoever wrote them, carrying the `generate.sage` that was beside them at the
time, and chained oldest to newest so the diff and restore machinery works
across the whole span.

Two things make this messier than "read the log":

The file was called `collection.yaml` until commit a504adb on 2021-03-20,
which renamed it to `table.yaml`. Looking only for the current name loses
every version before that date, and `git log --follow` does not recover them
either -- which is exactly the mistake that made this history look not worth
importing.

Content is normalised through `dump_tree`, the same path an edit takes, rather
than stored as the literal historical bytes. Otherwise every diff would be
dominated by formatting churn and the rename alone would read as a total
rewrite. The history is therefore faithful in content, not byte-for-byte.
"""

import os
import re
import subprocess

import yaml
from django.core.management.base import BaseCommand
from django.db import transaction

from data_pipeline.utils import normalize_table_data
from numberdb_app.editing import (attach_files, dump_tree,
                                  without_managed_keys)
from numberdb_app.models import Contributor, Table, TableRevision

#The document has gone by two names; see the module docstring.
DOCUMENT_NAMES = ('table.yaml', 'collection.yaml')

#Not attachments: these are the table itself, or the identifier the schema
#keeps out of the document deliberately.
NOT_ATTACHMENTS = {'table.yaml', 'collection.yaml', 'numbers.yaml',
                   'polynomials.yaml', 'id.yaml'}

MAX_FILE_BYTES = 8 * 1024 * 1024

#A GitHub no-reply address carries the account's numeric id, which is exactly
#what allauth stores as SocialAccount.uid. That makes the match to a site
#account exact rather than a guess at somebody's name.
GITHUB_NOREPLY = re.compile(r'^(\d+)\+.*@users\.noreply\.github\.com$', re.I)


def git(repo, *args):
	"""Run git and return stdout, or None if it failed."""
	done = subprocess.run(('git', '-C', repo) + args,
	                      capture_output=True)
	if done.returncode != 0:
		return None
	return done.stdout


def git_text(repo, *args):
	raw = git(repo, *args)
	if raw is None:
		return None
	try:
		return raw.decode('utf8')
	except UnicodeDecodeError:
		return None


class Command(BaseCommand):
	help = "Rebuild table histories from the data repository's git log."

	def add_arguments(self, parser):
		parser.add_argument('--root', default='/numberdb-data')
		parser.add_argument('--table', default='', help='one T-number')
		parser.add_argument('--dry-run', action='store_true')

	def handle(self, *args, **options):
		self.repo = options['root']
		self.dry = options['dry_run']
		self.users = self.account_index()

		tables = Table.objects.exclude(path='').exclude(path=None)
		if options['table']:
			tables = tables.filter(tid=options['table'])

		made = skipped = unreadable = 0
		for table in tables.order_by('tid_int'):
			states, bad = self.versions_of(table, count_bad=True)
			unreadable += bad
			if not states:
				continue
			if self.dry:
				self.stdout.write('%-6s %d version(s) %s .. %s'
				                  % (table.tid, len(states),
				                     states[0]['when'].split('T')[0],
				                     states[-1]['when'].split('T')[0]))
				made += len(states)
				continue
			with transaction.atomic():
				n, s = self.write_history(table, states)
			made += n
			skipped += s
			self.stdout.write('%-6s %d revision(s) written, %d already there'
			                  % (table.tid, n, s))

		self.stdout.write(self.style.SUCCESS(
			'%d revision(s), %d unchanged, %d version(s) unreadable'
			% (made, skipped, unreadable)))

	# -- reading the repository -------------------------------------------

	def versions_of(self, table, count_bad=False):
		"""Every distinct, loadable state of this table, oldest first."""
		log = git_text(self.repo, 'log', '--format=%H\t%aI\t%an\t%ae',
		               '--reverse', '--', table.path)
		states, bad, previous = [], 0, None
		for line in (log or '').strip().split('\n'):
			if not line:
				continue
			sha, when, name, email = line.split('\t')
			tree = self.document_at(sha, table.path)
			if tree is None:
				bad += 1
				continue
			content = dump_tree(without_managed_keys(tree))
			if content == previous:
				continue
			previous = content
			states.append({'sha': sha, 'when': when, 'name': name,
			               'email': email, 'content': content})
		return (states, bad) if count_bad else states

	def document_at(self, sha, path):
		"""The resolved table document at one commit, or None if it will not load."""
		for name in DOCUMENT_NAMES:
			text = git_text(self.repo, 'show', '%s:%s/%s' % (sha, path, name))
			if text is not None:
				break
		else:
			return None

		try:
			tree = yaml.load(text, Loader=yaml.BaseLoader)
		except yaml.YAMLError:
			return None
		if not isinstance(tree, dict):
			return None

		resolved = self.resolve(tree, sha, path)
		if resolved is None:
			return None
		if not any(k in resolved for k in ('Numbers', 'Data', 'Polynomials')):
			return None
		#The same normalisation the build applies before storing, so a
		#reconstructed version can be compared with what the table holds now.
		#Without it the newest reconstructed state differs from the stored one
		#in trivia -- `Formulas: ''` against `Formulas: {}` -- and the import
		#adds a spurious final revision instead of correcting the placeholder.
		try:
			return normalize_table_data(resolved)
		except Exception:
			return None

	def resolve(self, node, sha, path, depth=0):
		"""Expand INPUT{} against the repository as it was at that commit.

		The same rules as `data_pipeline.utils.load_yaml_recursively`, reading
		from a git tree instead of the working directory. `id.yaml` is allowed
		to be missing: it holds the identifier, which is a managed key and is
		stripped from the document anyway.
		"""
		if depth > 8:
			return None
		if isinstance(node, str):
			s = node.strip(' \n')
			if s.startswith('INPUT{') and s.endswith('}'):
				target = s[6:-1]
				text = git_text(self.repo, 'show',
				                '%s:%s/%s' % (sha, path, target))
				if text is None:
					return '' if target == 'id.yaml' else None
				try:
					inner = yaml.load(text, Loader=yaml.BaseLoader)
				except yaml.YAMLError:
					return None
				return self.resolve(inner, sha, path, depth + 1)
			return s
		if isinstance(node, list):
			out = []
			for item in node:
				value = self.resolve(item, sha, path, depth + 1)
				if value is None:
					return None
				out.append(value)
			return out
		if isinstance(node, dict):
			out = {}
			for key, value in node.items():
				if key in ('IGNORE', 'TODO'):
					continue
				resolved = self.resolve(value, sha, path, depth + 1)
				if resolved is None:
					return None
				out[key] = resolved
			return out
		return node

	def files_at(self, sha, path):
		"""The table's attachments as they were at one commit."""
		listing = git_text(self.repo, 'ls-tree', '-r', '--name-only',
		                   '%s' % (sha,), '--', path) or ''
		files = {}
		for full in listing.strip().split('\n'):
			if not full:
				continue
			relative = os.path.relpath(full, path)
			if os.path.basename(full) in NOT_ATTACHMENTS:
				continue
			raw = git(self.repo, 'show', '%s:%s' % (sha, full))
			if raw is None or len(raw) > MAX_FILE_BYTES:
				continue
			files[relative] = raw
		return files

	# -- attribution -------------------------------------------------------

	def account_index(self):
		"""Site accounts by email and by GitHub id, for exact matching."""
		from allauth.account.models import EmailAddress
		from allauth.socialaccount.models import SocialAccount
		from django.contrib.auth.models import User

		index = {}
		for user in User.objects.exclude(email=''):
			index['email:%s' % (user.email.lower(),)] = user
		for row in EmailAddress.objects.select_related('user'):
			index.setdefault('email:%s' % (row.email.lower(),), row.user)
		for row in SocialAccount.objects.select_related('user'):
			index['%s:%s' % (row.provider, row.uid)] = row.user
		return index

	def who(self, name, email):
		"""(user, contributor, produced_by) for one git identity.

		A bot is credited as a bot rather than as an author. `zeta3[bot]` has
		69 commits touching table directories, and counting those as authored
		edits would walk it past the trust threshold ahead of every human.
		"""
		if name.endswith('[bot]') or email.startswith('zeta3@'):
			return None, None, name

		user = None
		match = GITHUB_NOREPLY.match(email)
		if match:
			user = self.users.get('github:%s' % (match.group(1),))
		if user is None:
			user = self.users.get('email:%s' % (email.lower(),))

		contributor = None
		if not self.dry:
			contributor, _ = Contributor.objects.get_or_create(
				author_and_email='%s <%s>' % (name, email),
				defaults={'author': name, 'email': email},
			)
		return user, contributor, ''

	# -- writing -----------------------------------------------------------

	def write_history(self, table, states):
		"""Insert the reconstructed revisions beneath the table's current head.

		The newest reconstructed state is normally identical to what the table
		already holds, since that is what the import read. In that case the
		existing revision is corrected in place -- given its real date, author
		and message -- rather than duplicated, which is the whole point: it
		stops claiming the table appeared on the day of the import.

		Numbers are not rebuilt. These revisions are ancestors of the head, so
		nothing about what the site currently shows changes.
		"""
		head = table.head_revision
		known = {r.digest for r in table.revisions.all()}
		written = skipped = 0
		parent = None

		for index, state in enumerate(states):
			digest = TableRevision.digest_of(state['content'])
			last = index == len(states) - 1
			user, contributor, produced_by = self.who(state['name'],
			                                          state['email'])

			if last and head is not None and head.digest == digest:
				#Correct the placeholder rather than adding a twin.
				head.parent = parent
				head.author = user
				head.contributor = contributor
				head.produced_by = produced_by or 'data-repository history'
				head.message = 'imported from the data repository'
				head.save(update_fields=['parent', 'author', 'contributor',
				                         'produced_by', 'message'])
				TableRevision.objects.filter(pk=head.pk).update(
					created=state['when'])
				skipped += 1
				continue

			if digest in known and not last:
				skipped += 1
				continue

			revision = TableRevision.objects.create(
				table=table,
				content=state['content'],
				parent=parent,
				base=parent,
				author=user,
				contributor=contributor,
				produced_by=produced_by or 'data-repository history',
				message='from the data repository, %s' % (state['sha'][:8],),
			)
			#auto_now_add ignores anything passed in, so the real date has to
			#be written afterwards; a history stamped with today's date would
			#defeat the exercise.
			TableRevision.objects.filter(pk=revision.pk).update(
				created=state['when'])
			attach_files(revision, self.files_at(state['sha'], table.path))
			parent = revision
			written += 1

		#Every table must end with a revision holding what it holds now. A
		#table whose git path stops in 2021 -- several were restructured --
		#would otherwise have its head pointing at a five-year-old document,
		#and the editor would seed from that rather than from the present.
		if parent is not None:
			if head is None:
				current = dump_tree(without_managed_keys(
					yaml.load(table.data.full_yaml, Loader=yaml.BaseLoader)))
				head = TableRevision.objects.create(
					table=table, content=current, parent=parent, base=parent,
					produced_by='data-repository import',
					message='the current state of the data repository')
				attach_files(head, None, carry_from=parent)
				table.head_revision = head
				table.save(update_fields=['head_revision'])
				written += 1
			elif head.parent_id is None:
				head.parent = parent
				head.base = parent
				head.save(update_fields=['parent', 'base'])

		return written, skipped
