"""Three-way merge over a parsed table, rather than over its text.

Two people editing one table is the ordinary case, not the exceptional one: a
table holds thousands of entries and most edits touch one of them. Merging the
text of `numbers.yaml` would make those edits collide whenever they landed near
each other, and would also conflict on changes that are not changes at all --
a reflowed block scalar, a reordered mapping, an indentation fixed. None of
those alter what the table says.

So the merge happens on the tree. Two people editing entries `n=5` and `n=17`
are touching disjoint keys and never see a conflict; two people editing `n=5`
do, and are shown both versions. Formatting is not represented in the tree at
all, so it cannot conflict.

The rules are the familiar ones, with one deliberate departure:

  * a value changed on one side only takes the changed value;
  * a value changed the same way on both sides takes it once;
  * a value changed differently on each side is a conflict;
  * a key added on one side is added; added on both with the same value is
    fine, with different values is a conflict;
  * a key deleted on one side and untouched on the other is deleted;
  * a key deleted on one side and modified on the other is a conflict, never a
    silent deletion. Losing an entry quietly is the worst outcome available,
    because nothing about the result looks wrong.

The departure is lists. They are compared whole rather than element by element:
`Tags`, `sources` and `group parameters` are short, ordered, and their order
carries meaning, so a positional merge would invent orderings nobody chose. Two
different edits to one list are a conflict even if they look combinable.

Nothing here writes YAML. The caller merges trees and serialises once, which is
what keeps formatting out of the conflict set.
"""

from __future__ import annotations

__all__ = ['merge', 'Conflict', 'MergeResult']


class Conflict:
	"""One place where the two sides disagree and the merge cannot decide.

	``path`` is the sequence of keys from the root, so it can be shown to a
	person as ``Numbers > 5 > comment`` and used to anchor the resolution UI.
	"""

	__slots__ = ('path', 'base', 'mine', 'theirs', 'kind')

	def __init__(self, path, base, mine, theirs, kind='value'):
		self.path = tuple(path)
		self.base = base
		self.mine = mine
		self.theirs = theirs
		#'value'  both sides changed it differently
		#'delete' one side deleted what the other changed
		#'type'   the two sides made it different kinds of thing
		self.kind = kind

	def __repr__(self):
		return 'Conflict(%s, kind=%r)' % (' > '.join(str(p) for p in self.path),
		                                  self.kind)

	def __eq__(self, other):
		return (isinstance(other, Conflict) and self.path == other.path
		        and self.kind == other.kind and self.base == other.base
		        and self.mine == other.mine and self.theirs == other.theirs)


class MergeResult:
	"""The merged tree, and everywhere it had to guess nothing."""

	__slots__ = ('tree', 'conflicts')

	def __init__(self, tree, conflicts):
		self.tree = tree
		self.conflicts = conflicts

	@property
	def clean(self):
		return not self.conflicts

	def __repr__(self):
		return 'MergeResult(clean=%s, conflicts=%d)' % (self.clean,
		                                               len(self.conflicts))


#A sentinel for "this key is not present", which is distinct from a key whose
#value is None. `Comments:` with nothing under it is None and is a real state
#of a table; a missing key is not.
class _Missing:
	_instance = None

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __repr__(self):
		return '<missing>'


MISSING = _Missing()


def merge(base, mine, theirs):
	"""Merge ``mine`` and ``theirs``, both derived from ``base``.

	Returns a :class:`MergeResult`. Where the two sides conflict, the merged
	tree keeps **my** value, so the result is always a usable document; the
	conflict list says where that choice was arbitrary and needs a human.
	"""
	conflicts = []
	tree = _merge_node(base, mine, theirs, (), conflicts)
	return MergeResult(tree, conflicts)


def _merge_node(base, mine, theirs, path, conflicts):
	#Identical sides need no examination, whatever they contain. This is also
	#what makes a merge of two untouched subtrees cost nothing.
	if _same(mine, theirs):
		return _copy(mine)

	#One side did not touch it, so the other side's version is the answer. This
	#is the case that makes disjoint edits free.
	if _same(base, mine):
		return _copy(theirs)
	if _same(base, theirs):
		return _copy(mine)

	#Both sides changed it, differently.

	if mine is MISSING or theirs is MISSING:
		#One deleted what the other edited. Never resolved silently: the
		#deletion is plausible and so is the edit, and choosing wrongly loses
		#an entry without leaving a trace.
		conflicts.append(Conflict(path, base, mine, theirs, kind='delete'))
		return _copy(mine if mine is not MISSING else theirs)

	if isinstance(mine, dict) and isinstance(theirs, dict):
		merged = {}
		base_dict = base if isinstance(base, dict) else {}
		#Ordered by first appearance rather than sorted: a table's keys are in
		#a deliberate order, and sorting them would rewrite every file.
		for key in _ordered_keys(base_dict, mine, theirs):
			sub = _merge_node(
				base_dict.get(key, MISSING),
				mine.get(key, MISSING),
				theirs.get(key, MISSING),
				path + (key,),
				conflicts,
			)
			if sub is not MISSING:
				merged[key] = sub
		return merged

	#Lists are compared whole; see the module docstring.
	if isinstance(mine, list) and isinstance(theirs, list):
		conflicts.append(Conflict(path, base, mine, theirs, kind='value'))
		return _copy(mine)

	if type(mine) is not type(theirs):
		conflicts.append(Conflict(path, base, mine, theirs, kind='type'))
		return _copy(mine)

	conflicts.append(Conflict(path, base, mine, theirs, kind='value'))
	return _copy(mine)


def _ordered_keys(base, mine, theirs):
	"""Every key across the three, in the order a reader would expect.

	Base order first, since that is the document's existing shape, then keys
	added by either side in the order they appear.
	"""
	seen = []
	for source in (base, mine, theirs):
		if not isinstance(source, dict):
			continue
		for key in source:
			if key not in seen:
				seen.append(key)
	return seen


def _same(a, b):
	if a is MISSING or b is MISSING:
		return a is b
	return a == b


def _copy(value):
	if value is MISSING:
		return MISSING
	if isinstance(value, dict):
		return {k: _copy(v) for k, v in value.items()}
	if isinstance(value, list):
		return [_copy(v) for v in value]
	return value
