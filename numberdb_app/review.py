"""Which values in a table are unreviewed.

Every commit is live the moment it is made, so review does not gate whether
something is published. It gates one thing: whether a value is allowed into
search by number.

That asymmetry is what makes immediate publication safe here. A reader who
lands on a page can see the entry is unreviewed and judge it. A person typing a
number into the search bar cannot, because a wrong fortieth digit looks exactly
like a right one, and the whole point of the site is that finding a number in
it means something.

The unreviewed set is the *difference* between the last reviewed revision and
head, not the whole table. Correcting one comment must not cast doubt on ten
thousand untouched entries, or the gate becomes so coarse that reviewing stops
being worth anybody's time.

A table nobody has reviewed has no reviewed revision, and then everything in it
is unreviewed. That is the honest default for something newly created, and it
gives review an obvious purpose: an entry is not findable by value until
somebody has confirmed it.
"""

from __future__ import annotations

__all__ = ['changed_params', 'unreviewed_params', 'flatten_entries',
           'ALL_UNREVIEWED']


#: A dict carrying any of these is an entry, not another level of parameter.
#: Taken from the renderer, so the two agree about where the parameters stop:
#: a table whose parameter happened to be called "number" would otherwise be
#: flattened differently by each.
ENTRY_MARKERS = frozenset(('number', 'numbers', 'datum', 'data', 'equals'))

#: Returned when a table has never been reviewed at all. Distinct from the
#: empty set, which means "reviewed, and nothing has changed since".
ALL_UNREVIEWED = object()


def flatten_entries(numbers):
	"""Map every entry to its parameter identity.

	The identity is the comma-joined parameter values, which is what
	``Number.param_str()`` produces and what the page anchors on, so a caller
	can match these against stored rows without a translation step.

	The descent mirrors the renderer, because the two must agree about where
	the parameters stop. In particular a dict carrying ``number`` or ``numbers``
	is *not* the end of the walk: it holds a value or a further container at
	the **same** parameter depth, alongside things like ``param-latex``. Taking
	it as terminal collapses a table such as T33, which is shaped

	    Numbers -> a_n -> {param-latex, numbers -> {0, 1, 2, ...}}

	from five hundred entries down to two.
	"""
	flat = {}

	def walk(node, prefix):
		if isinstance(node, list):
			#The normalised shape the editing path writes: a list of entries,
			#each carrying its own `params`. Without this the walk records the
			#whole list under one identity, so a table of 1080 entries has one,
			#matching nothing in the shape it was reviewed in -- and every
			#entry counts as changed. That is what took the corpus out of
			#search by number.
			#Only when the entries are actually distinguished by parameters.
			#A table whose values are a bare list has `params: {}` on every
			#entry, and keying by that gives every one of them the same
			#identity -- T67's 442 values collapsed onto one, and the last
			#one won.
			if (node and all(isinstance(item, dict) and 'params' in item
			                 for item in node)
					and any(item.get('params') for item in node)):
				for item in node:
					values = (item.get('params') or {}).values()
					identity = ','.join(_normalise_param(value)
					                    for value in values)
					flat[identity or ','.join(prefix)] = item
				return
			#A table with no parameters is a list of one bare value; record
			#the value, not the list, so it can be compared with the same
			#entry written the other way.
			if len(node) == 1:
				walk(node[0], prefix)
				return
			flat[','.join(prefix)] = node
			return

		if isinstance(node, dict):
			if set(node) & ENTRY_MARKERS:
				#`numbers` holds further entries at the same parameter depth,
				#beside metadata such as param-latex, so the walk continues
				#into it. T33 is shaped
				#    Numbers -> a_n -> {param-latex, numbers -> {0, 1, ...}}
				#and treating that dict as terminal collapses five hundred
				#entries into two.
				if 'numbers' in node and isinstance(node['numbers'], dict):
					walk(node['numbers'], prefix)
					return
				#Otherwise this dict *is* the entry, and it is recorded whole
				#rather than reduced to node['number']: a changed comment or
				#proof is a change to the entry, and comparing only the value
				#would let it pass unreviewed.
				flat[','.join(prefix)] = node
				return
			for key, value in node.items():
				walk(value, prefix + (_normalise_param(key),))
			return
		flat[','.join(prefix)] = node

	walk(numbers if numbers is not None else {}, ())
	return flat


def _normalise_param(key):
	"""A parameter key as the stored rows spell it.

	A key holding several values is written `64, 296` in the YAML and stored as
	`64,296`, because the renderer strips the spaces when it builds the anchor.
	Without the same normalisation here, every identity in the ten tables that
	group parameters this way fails to match its own row, and the review gate
	would silently apply to nothing.
	"""
	return ','.join(part.strip() for part in str(key).split(','))


def _entries_of(tree):
	"""The entry section of a table, under whichever key it uses."""
	if not isinstance(tree, dict):
		return {}
	#`Data` is the old spelling; the corpus was normalised to `Numbers`, but a
	#revision committed before that still says Data and must still diff.
	section = tree.get('Numbers')
	if section is None:
		section = tree.get('Data')
	return section if isinstance(section, (dict, list)) else {}


def _same_entry(one, other):
	"""Whether two recorded entries say the same thing.

	Not `==`. The same entry is held in the corpus in more than one shape --

	    Numbers: ['3.14159...']                             # as imported
	    Numbers: [{'params': {}, 'number': '3.14159...'}]   # as rewritten

	-- and normalising a tree also moves annotations about: `param-latex` off
	the entry, `url` and `both signs` down onto it from the node above. None of
	that changes what the table asserts about a number, and comparing it
	literally said every entry in the corpus had changed. It did: 71% of stored
	reals, and every complex, p-adic and polynomial value, left search by
	number, which holds unreviewed values back.

	So: `params` is dropped, being the identity these are keyed by. `number`
	must agree. Any other key present on *both* sides must agree -- a changed
	comment or proof is a change to the entry, and comparing only the value
	would let it pass unreviewed. A key on one side only is relocation, and
	is not a claim about the digits that a reviewer confirmed.

	Measured over the whole corpus when this was written: 2124 entries
	differed only in `param-latex`, 1075 in `url`, 1075 in `both signs`, and
	43 in `number`. The 43 are the ones review is for.
	"""
	def canonical(node):
		#Recursive, because `flatten_entries` need not descend into a list: a
		#table whose entries are a bare list can arrive here whole.
		if isinstance(node, list):
			return [canonical(item) for item in node]
		if isinstance(node, dict):
			return {key: value for key, value in node.items()
			        if key != 'params'}
		return {'number': node}

	def same(one, other):
		if isinstance(one, list) or isinstance(other, list):
			if not (isinstance(one, list) and isinstance(other, list)):
				return False
			return (len(one) == len(other)
			        and all(same(a, b) for a, b in zip(one, other)))
		#`number: ['-188.5']` and `number: '-188.5'` are the same claim: the
		#normalised shape wraps a lone value in a list. T68 differed in 187
		#entries by nothing else.
		def value_of(entry):
			number = entry.get('number')
			if isinstance(number, list) and len(number) == 1:
				return number[0]
			return number

		if value_of(one) != value_of(other):
			return False
		#`number` is settled above, by a comparison that knows a lone value may
		#be wrapped in a list; comparing it again literally undoes that.
		return all(one[key] == other[key]
		           for key in (set(one) & set(other)) - {'number'})

	return same(canonical(one), canonical(other))


def changed_params(before_tree, after_tree):
	"""Parameter identities whose value differs between two trees.

	Includes entries added and entries removed: a removal is a change to what
	the table asserts, and a search that kept returning a value somebody had
	deleted would be worse than one that briefly forgot it.
	"""
	before = flatten_entries(_entries_of(before_tree))
	after = flatten_entries(_entries_of(after_tree))
	changed = set()
	for key in set(before) | set(after):
		one, other = before.get(key, _ABSENT), after.get(key, _ABSENT)
		if one is _ABSENT or other is _ABSENT or not _same_entry(one, other):
			changed.add(key)
	return changed


class _Absent:
	def __repr__(self):
		return '<absent>'


_ABSENT = _Absent()


def unreviewed_params(table):
	"""Which of ``table``'s entries have not been reviewed.

	Returns :data:`ALL_UNREVIEWED` when nobody has reviewed the table, a set of
	parameter identities otherwise, and an empty set when review is current.
	"""
	from .editing import tree_of

	if table.head_revision_id is None:
		#Nothing has been committed through the editing path, so the table is
		#whatever the data repository built. That corpus is reviewed by
		#construction: it arrived through pull requests.
		return set()

	if table.reviewed_at_revision_id is None:
		return ALL_UNREVIEWED

	if table.reviewed_at_revision_id == table.head_revision_id:
		return set()

	return changed_params(tree_of(table.reviewed_at_revision),
	                      tree_of(table.head_revision))


def sync_review_flags(table):
	"""Set the ``reviewed`` flag on every row of ``table`` from its history.

	Returns the number of rows now marked unreviewed.

	Called after a commit and after a review, so the flag always describes the
	table's current head rather than whatever was true when the row was built.
	Cheap enough to do wholesale: it is two updates per number kind, and the
	tables that get edited are the ones somebody is looking at.
	"""
	from .models import Number, NumberComplex, NumberPAdic, Polynomial

	outstanding = unreviewed_params(table)
	kinds = (Number, NumberComplex, NumberPAdic, Polynomial)

	if outstanding is ALL_UNREVIEWED:
		return sum(model.objects.filter(table=table).update(reviewed=False)
		           for model in kinds)

	marked = 0
	for model in kinds:
		rows = list(model.objects.filter(table=table).only('id', 'param'))
		if not rows:
			continue
		#Compared in Python rather than in SQL because `param` is a binary
		#column and the identities are text; pushing this into the query would
		#mean encoding every identity the same way the builder did, which is
		#exactly the mismatch that made the first version of this gate apply to
		#nothing at all.
		unreviewed_ids = [r.id for r in rows if r.param_str() in outstanding]
		reviewed_ids = [r.id for r in rows if r.param_str() not in outstanding]
		if unreviewed_ids:
			marked += model.objects.filter(id__in=unreviewed_ids).update(
				reviewed=False)
		if reviewed_ids:
			model.objects.filter(id__in=reviewed_ids).update(reviewed=True)
	return marked
