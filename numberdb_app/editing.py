"""Committing an edited table.

The one entry point is :func:`commit_table`. It takes the tree a person edited
and the revision they started from, and does whatever is needed to get that
edit onto the table's history without losing anybody's work:

  * nobody else committed in the meantime, so the edit applies directly;
  * somebody did, and the two edits touch different things, so they are merged
    and the merge is itself a commit;
  * somebody did, and the two edits touch the same thing, so nothing is
    written and the conflicts are handed back for a person to resolve.

The third case is the reason this is a function rather than a `.save()`. A
stale write that silently wins is the failure this whole design exists to
avoid, and it is invisible afterwards: the table looks fine and somebody's
correction is simply gone.

Serialisation happens here, once, at the end. Everything upstream works on
trees, which is what keeps formatting out of the conflict set: two people who
reindent the same file have not made conflicting changes, and the merge never
sees the indentation to disagree about.
"""

from __future__ import annotations

import re

import yaml

from .merge import merge

__all__ = ['commit_table', 'CommitOutcome', 'StaleEdit', 'tree_of', 'dump_tree']



class ParametersChanged(Exception):
	"""The edit alters the table's parameters, which no ordinary edit may do.

	Every entry's identity is its parameter values, so changing the set or the
	order of parameters silently reassigns every identity in the table. Old
	citations do not break: `1,2` still exists and now means a different
	number. Anchors, search results, cross-references from other tables and the
	review diff all follow suit, and nothing anywhere reports a problem.

	Renaming is not the same as reordering and is not refused here, since the
	identity is built from the values; but it does invalidate any citation
	written in the named form, which is why it is worth saying out loud too.
	"""

	def __init__(self, before, after):
		self.before = before
		self.after = after
		super().__init__('parameters would change from %s to %s'
		                 % (list(before), list(after)))


def parameters_of(tree):
	"""The parameter names a document declares, in order."""
	if not isinstance(tree, dict):
		return []
	return list((tree.get('Parameters') or {}).keys())


class StaleEdit(Exception):
	"""The edit was written against a revision that has since been superseded,
	and the two changes cannot be reconciled without a person.

	Carries the conflicts and the merged tree so far, so the caller can render
	a resolution screen rather than only an apology.
	"""

	def __init__(self, conflicts, tree, head):
		self.conflicts = conflicts
		self.tree = tree
		self.head = head
		super().__init__('%d conflict(s) against revision %s'
		                 % (len(conflicts), head.digest[:8]))


class CommitOutcome:
	"""What happened, for the caller to report."""

	__slots__ = ('revision', 'merged', 'unchanged', 'breaches')

	def __init__(self, revision, merged=False, unchanged=False, breaches=()):
		self.revision = revision
		#: Soft size limits this table is over without saying why. It was
		#: committed regardless, because the author may have a good reason and
		#: the review queue is where reasons are judged.
		self.breaches = list(breaches)
		#: True when somebody else had committed and the two edits were
		#: combined. Worth telling the author, since the result contains
		#: changes they have not seen.
		self.merged = merged
		#: True when the edit turned out to change nothing. No revision is
		#: created; the existing head is returned.
		self.unchanged = unchanged

	def __repr__(self):
		return ('CommitOutcome(%s, merged=%s, unchanged=%s)'
		        % (self.revision.digest[:8] if self.revision else None,
		           self.merged, self.unchanged))


def tree_of(revision):
	"""The parsed tree of a revision.

	``BaseLoader`` because that is what every other reader in this codebase
	uses: it returns strings and coerces nothing, so `complete: no` stays the
	word `no` rather than becoming a boolean. A merge that used a different
	loader from the renderer would compare values the renderer never sees.
	"""
	if revision is None:
		return {}
	return yaml.load(revision.content, Loader=yaml.BaseLoader) or {}


def dump_tree(tree):
	"""A tree as the YAML that gets stored.

	``sort_keys=False`` because a table's keys are in a deliberate order and
	sorting them would rewrite every file on first save, burying the actual
	edit in an unreadable diff.
	"""
	return yaml.dump(tree, sort_keys=False, allow_unicode=True,
	                 default_flow_style=False)


def commit_table(table, tree, author=None, message='', base=None,
                 produced_by='', allow_parameter_change=False, strict=False,
                 files=None):
	"""Put ``tree`` on ``table``'s history and return a :class:`CommitOutcome`.

	``base`` is the revision the author started from. Passing None means "this
	is the first revision" for an empty history, and "I did not look" for a
	table that already has one, which is treated as editing from head.

	Raises :class:`StaleEdit` when the edit cannot be reconciled. Nothing is
	written in that case, so a caller may show the conflicts and let the author
	try again without having half-committed anything.

	``strict`` refuses a table that is over a soft size limit without saying
	why, instead of committing it and reporting the breach. It is for writers
	that cannot be warned -- the API, and bulk machine proposals -- since a
	warning shown to nobody is not a limit at all.

	Soft breaches that were committed anyway come back on the outcome, for the
	caller to show and the review queue to raise.

	``files`` maps a name to bytes, or to None to delete it. Anything not
	mentioned is carried forward from the base, so an edit to the YAML alone
	keeps the table's scripts without saying anything about them.
	"""
	from .limits import enforce
	from .models import TableRevision

	head = table.head_revision

	#Both checks run before any of the paths below, because all of them write.
	breaches = enforce(tree, strict=strict)

	if head is not None and not allow_parameter_change:
		before = parameters_of(tree_of(head))
		after = parameters_of(tree)
		if before and before != after:
			raise ParametersChanged(before, after)

	if head is None:
		return _write(table, tree, author, message, parent=None, base=None,
		              produced_by=produced_by, breaches=breaches, files=files)

	if base is None or base.pk == head.pk:
		#Nobody moved. The ordinary case, and the fast one.
		content = dump_tree(tree)
		if (TableRevision.digest_of(content) == head.digest
		    and not _files_change(head, files)):
			return CommitOutcome(head, unchanged=True, breaches=breaches)
		return _write(table, tree, author, message, parent=head, base=head,
		              produced_by=produced_by, breaches=breaches, files=files)

	#Somebody committed while this edit was being written.
	result = merge(tree_of(base), tree, tree_of(head))
	if result.conflicts:
		raise StaleEdit(result.conflicts, result.tree, head)

	#Files merge on the same three-way rules, and a clash in them is as much a
	#reason to stop as a clash in the document: overwriting somebody's script
	#is no better than overwriting their numbers.
	merged_files, file_conflicts = merge_manifests(
		manifest_of(base), _wanted_manifest(base, files), manifest_of(head))
	if file_conflicts:
		raise StaleEdit([('file: %s' % (name,)) for name in file_conflicts],
		                result.tree, head)

	content = dump_tree(result.tree)
	if (TableRevision.digest_of(content) == head.digest
	    and merged_files == manifest_of(head)):
		#The edit was already contained in what the other person committed.
		return CommitOutcome(head, unchanged=True, breaches=breaches)

	return _write(table, result.tree, author, message, parent=head, base=base,
	              produced_by=produced_by, merged=True, breaches=breaches,
	              manifest=merged_files)


def _files_change(revision, files):
	"""Whether ``files`` would alter what ``revision`` already carries."""
	return _wanted_manifest(revision, files) != manifest_of(revision)


def _wanted_manifest(revision, files):
	"""The manifest ``files`` asks for, on top of what ``revision`` has.

	The bytes are stored as they are named. Computing a digest without storing
	the blob it describes produces a manifest pointing at nothing, and the
	failure is silent: the revision is written, the attachment is missing, and
	the only symptom is a file that quietly disappeared during a merge.
	"""
	from .models import Blob

	wanted = dict(manifest_of(revision))
	for name, data in (files or {}).items():
		if data is None:
			wanted.pop(name, None)
		elif isinstance(data, Blob):
			wanted[name] = data.digest
		else:
			wanted[name] = Blob.store(data).digest
	return wanted


def _write(table, tree, author, message, parent, base, produced_by,
           merged=False, breaches=(), files=None, manifest=None):
	from .models import TableRevision

	revision = TableRevision.objects.create(
		table = table,
		content = dump_tree(tree),
		parent = parent,
		base = base,
		author = author,
		message = message,
		produced_by = produced_by,
	)
	#Before head moves, so a revision is never briefly visible without the
	#files it was committed with.
	if manifest is not None:
		_attach_manifest(revision, manifest)
	else:
		attach_files(revision, files, carry_from=parent)

	table.head_revision = revision
	#A board member's own edit is reviewed by the act of making it; that
	#decision belongs to the caller, which knows who the author is, so this
	#only advances head.
	table.save(update_fields=['head_revision'])
	apply_revision(table, revision)
	return CommitOutcome(revision, merged=merged, breaches=breaches)


def _attach_manifest(revision, manifest):
	"""Record an already-resolved {name: digest} manifest on a revision."""
	from .models import Attachment, Blob

	blobs = {b.digest: b for b in
	         Blob.objects.filter(digest__in=set(manifest.values()))}
	missing = sorted(n for n, d in manifest.items() if d not in blobs)
	if missing:
		#Loudly, because the alternative is a revision that silently lost a
		#file and looks perfectly normal afterwards.
		raise ValueError('manifest names blobs that are not stored: %s'
		                 % (', '.join(missing),))
	Attachment.objects.bulk_create([
		Attachment(revision=revision, name=name, blob=blobs[digest])
		for name, digest in sorted(manifest.items())
	])


def apply_revision(table, revision=None):
	"""Make the stored rows and the page match a revision.

	A revision on its own changes nothing anybody can see: the page renders
	from ``TableData`` and search reads the number rows, both of which are
	built by the data pipeline. Without this step an edit would be recorded
	and invisible, which is worse than an edit that fails.

	Three things happen, in this order, because each depends on the last:
	the table's stored document is replaced, its number rows are rebuilt from
	that document, and the review flags are recomputed so the newly written
	rows carry the right state rather than the default.
	"""
	from data_pipeline.build import build_number_table
	from db_builder.utils import normalize_table_data
	from .models import TableData
	from .review import sync_review_flags

	revision = revision or table.head_revision
	if revision is None:
		return

	tree = tree_of(revision)
	normalised = normalize_table_data(tree)

	data, _ = TableData.objects.get_or_create(table=table)
	data.json = normalised
	data.full_yaml = yaml.dump(normalised, sort_keys=False, allow_unicode=True)
	data.raw_yaml = revision.content
	data.save()

	build_number_table(only_table=table)
	#After the rebuild, not before: the rows it writes take the model default,
	#which is reviewed, and this is what corrects them.
	return sync_review_flags(table)


#The template a new table starts from. Every key the corpus uses, in the order
#it uses them, so a new table looks like the others from its first save and a
#contributor can see what is expected rather than having to find an example.
NEW_TABLE_TEMPLATE = """\
Title: {title}

Definition: >
  What these numbers are. One or two sentences, LaTeX allowed.

Parameters:

Comments:

Formulas:

Programs:

References:

Links:

Similar tables:

Keywords:

Tags:

Data properties:
  type: R
  complete: no

Display properties:

Numbers:
- 3.14159
"""


def slug_for(title, taken=None):
	"""A URL for a new table, derived from its title.

	The URL pattern accepts word characters, apostrophes, parentheses and
	hyphens, so everything else becomes an underscore. Existing tables are
	named this way (`Rational_multiples_of_pi`), and matching them matters
	because the slug is what people paste into papers.

	A number is appended only on collision, so the common case reads cleanly.
	"""
	from .models import Table

	base = re.sub(r"[^\w'()-]+", '_', (title or '').strip()).strip('_')
	base = re.sub(r'_+', '_', base) or 'table'
	base = base[:90]

	taken = taken if taken is not None else set(
		Table.objects.values_list('url', flat=True))
	if base not in taken:
		return base
	for n in range(2, 1000):
		candidate = '%s_%d' % (base, n)
		if candidate not in taken:
			return candidate
	raise ValueError('could not find a free url for %r' % (title,))


def create_table(tree, author=None, message='', produced_by='', strict=False):
	"""Create a table from a document and return it.

	The T-number is allocated here rather than in the data repository, which is
	what makes this site the place tables come into existence. It was
	previously handed out by `next_ids.yaml`, a file the repository maintained
	and the note at its head told everybody not to edit.

	Allocation takes the next integer above the highest in use, inside the same
	transaction as the row that claims it, so two people creating a table at
	once cannot receive the same number.
	"""
	from django.db import transaction
	from django.db.models import Max

	from .models import Table, TableData

	title = (tree.get('Title') or '').strip() if isinstance(tree, dict) else ''
	if not title:
		raise ValueError('A new table needs a Title.')

	if not has_entries(tree):
		raise ValueError(
			'A new table needs at least one entry. A table with no numbers in '
			'it is a draft, and a draft published here is indistinguishable '
			'from a table somebody abandoned: it holds a permanent T-number, '
			'appears in the listings and answers nothing. Enter one value by '
			'hand -- a program can add the rest afterwards.')

	#Titles are unique in the schema, so this would otherwise surface as a
	#database error page after the author had written the whole document.
	existing = Table.objects.filter(title=title).first()
	if existing is not None:
		raise ValueError(
			'A table called %r already exists (%s). Give this one a title that '
			'distinguishes it, or edit the existing table instead.'
			% (title, existing.tid))

	#One transaction around the number and the first revision both, so a
	#document refused for being over a hard limit leaves no half-made table
	#holding a T-number that will never be used again.
	with transaction.atomic():
		highest = (Table.objects.select_for_update()
		           .aggregate(Max('tid_int'))['tid_int__max'] or 0)
		number = highest + 1
		table = Table.objects.create(
			tid='T%d' % (number,),
			tid_int=number,
			url=slug_for(title),
			#Null, not empty: a table created here has no file in the
			#repository, and the column is unique, so the second such table
			#would collide with the first.
			path=None,
			title=title,
			title_lowercase=title.lower(),
			number_count=0,
		)
		TableData.objects.create(table=table, raw_yaml='', full_yaml='',
		                         json={})

		commit_table(table, tree, author=author,
		             message=message or 'created this table',
		             produced_by=produced_by, strict=strict)
	table.refresh_from_db()
	return table


#: Keys the site owns, which a person editing a table should neither see nor be
#: able to change. `ID` is the table's permanent identifier: it lives in the
#: Table row, it was never meant to be typed, and in the repository it was
#: filled in by a macro pointing at a file whose first line reads "Automatically
#: created file. Do NOT edit."
MANAGED_KEYS = ('ID',)


def has_entries(tree):
	"""Whether a document actually holds a number.

	A table is a place numbers live, so one with none is not a small table, it
	is a different kind of thing -- a draft. Drafts are not published here: a
	public draft holds a permanent T-number and looks exactly like a table
	somebody gave up on, and if it is later abandoned that number is either
	burnt or becomes a citation to nothing.

	A draft, when there is one, will carry an identifier of its own that turns
	into a T-number only when it is published.
	"""
	from .flatten import entries_block

	block = entries_block(tree)
	if block is None:
		return False
	return len(block) > 0


def without_managed_keys(tree):
	"""A document as the author should see it."""
	if not isinstance(tree, dict):
		return tree
	return {k: v for k, v in tree.items() if k not in MANAGED_KEYS}


def with_managed_keys(tree, table):
	"""A document as it is stored, with the site's own keys restored.

	Put back rather than trusted from the form: whatever the author typed for
	ID is ignored, so an identifier cannot be changed by editing text, and a
	table cannot be given somebody else's.
	"""
	if not isinstance(tree, dict):
		return tree
	restored = {'ID': table.tid}
	for k, v in tree.items():
		if k not in MANAGED_KEYS:
			restored[k] = v
	return restored


def restore_revision(table, revision, author=None, message=''):
	"""Put a table back to an earlier revision.

	Committed forward rather than rewound: the old content becomes a new
	revision, so the history says what happened and when, and the mistake stays
	visible instead of being quietly removed. That is what makes the whole
	publish-immediately arrangement bearable -- an edit can be undone by
	anybody, at once, and undoing it is itself an ordinary, reviewable act.

	Parameters are exempt from the usual freeze here. If an edit changed them,
	refusing to restore would leave the table stuck in exactly the state the
	freeze exists to prevent.
	"""
	if revision.table_id != table.pk:
		raise ValueError('that revision belongs to another table')

	#Files as well as numbers. Restoring the document alone would leave the
	#table describing one set of values with the script that produced a
	#different set sitting beside it, which is worse than either version.
	then = {a.name: a.blob for a in revision.attachments.select_related('blob')}
	files = dict(then)
	for name in manifest_of(table.head_revision):
		files.setdefault(name, None)

	return commit_table(
		table, tree_of(revision),
		author=author,
		message=message or ('restored the version from %s'
		                    % (revision.created.strftime('%Y-%m-%d %H:%M'),)),
		base=table.head_revision,
		allow_parameter_change=True,
		files=files,
	)


def manifest_of(revision):
	"""The complete set of files a revision has, as {name: blob digest}."""
	if revision is None:
		return {}
	return {a.name: a.blob.digest
	        for a in revision.attachments.select_related('blob')}


def attach_files(revision, files, carry_from=None):
	"""Record this revision's complete file manifest.

	``files`` maps a name to bytes, to a :class:`Blob`, or to None to say the
	file is gone as of this revision. Everything in ``carry_from`` that is not
	mentioned is carried forward unchanged, which is what makes an ordinary
	edit -- one that touches only the YAML -- keep the table's scripts without
	the caller having to say so.

	Carrying forward is a copy of the *manifest row*, never of the bytes: both
	revisions point at the same blob, so an unchanged 477 KB attachment costs
	nothing on the second revision.
	"""
	from .models import Attachment, Blob

	wanted = dict(manifest_of(carry_from))
	blobs = {}
	for name, data in (files or {}).items():
		if data is None:
			wanted.pop(name, None)
			continue
		blob = data if isinstance(data, Blob) else Blob.store(data)
		blobs[blob.digest] = blob
		wanted[name] = blob.digest

	missing = [d for d in wanted.values() if d not in blobs]
	if missing:
		blobs.update({b.digest: b for b in Blob.objects.filter(digest__in=missing)})

	absent = sorted(n for n, d in wanted.items() if d not in blobs)
	if absent:
		raise ValueError('manifest names blobs that are not stored: %s'
		                 % (', '.join(absent),))

	Attachment.objects.bulk_create([
		Attachment(revision=revision, name=name, blob=blobs[digest])
		for name, digest in sorted(wanted.items())
	])
	return wanted


def merge_manifests(base, mine, theirs):
	"""Three-way merge of two file manifests.

	Deliberately the same rules as the document merge, since the surprises are
	the same ones: a file both sides changed is a conflict, a file one side
	changed is taken, and a file deleted on one side and changed on the other
	is a conflict rather than a silent choice between losing the change and
	resurrecting the file.
	"""
	conflicts = []
	result = dict(theirs)

	for name in set(base) | set(mine) | set(theirs):
		was = base.get(name)
		ours = mine.get(name)
		yours = theirs.get(name)
		if ours == yours:
			continue
		if was == ours:
			#We did not touch it; whatever they did stands.
			continue
		if was == yours:
			#They did not touch it; our change applies.
			if ours is None:
				result.pop(name, None)
			else:
				result[name] = ours
			continue
		conflicts.append(name)

	return result, conflicts
