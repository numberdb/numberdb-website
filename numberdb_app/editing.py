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

import yaml

from .merge import merge

__all__ = ['commit_table', 'CommitOutcome', 'StaleEdit', 'tree_of', 'dump_tree']


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

	__slots__ = ('revision', 'merged', 'unchanged')

	def __init__(self, revision, merged=False, unchanged=False):
		self.revision = revision
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
                 produced_by=''):
	"""Put ``tree`` on ``table``'s history and return a :class:`CommitOutcome`.

	``base`` is the revision the author started from. Passing None means "this
	is the first revision" for an empty history, and "I did not look" for a
	table that already has one, which is treated as editing from head.

	Raises :class:`StaleEdit` when the edit cannot be reconciled. Nothing is
	written in that case, so a caller may show the conflicts and let the author
	try again without having half-committed anything.
	"""
	from .models import TableRevision

	head = table.head_revision

	if head is None:
		return _write(table, tree, author, message, parent=None, base=None,
		              produced_by=produced_by)

	if base is None or base.pk == head.pk:
		#Nobody moved. The ordinary case, and the fast one.
		content = dump_tree(tree)
		if TableRevision.digest_of(content) == head.digest:
			return CommitOutcome(head, unchanged=True)
		return _write(table, tree, author, message, parent=head, base=head,
		              produced_by=produced_by)

	#Somebody committed while this edit was being written.
	result = merge(tree_of(base), tree, tree_of(head))
	if result.conflicts:
		raise StaleEdit(result.conflicts, result.tree, head)

	content = dump_tree(result.tree)
	if TableRevision.digest_of(content) == head.digest:
		#The edit was already contained in what the other person committed.
		return CommitOutcome(head, unchanged=True)

	return _write(table, result.tree, author, message, parent=head, base=base,
	              produced_by=produced_by, merged=True)


def _write(table, tree, author, message, parent, base, produced_by,
           merged=False):
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
	table.head_revision = revision
	#A board member's own edit is reviewed by the act of making it; that
	#decision belongs to the caller, which knows who the author is, so this
	#only advances head.
	table.save(update_fields=['head_revision'])
	return CommitOutcome(revision, merged=merged)
