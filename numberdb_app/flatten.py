"""Entries as flat records with named parameters.

The nested form asks a question the data cannot answer: given a mapping, is
this another parameter level or is this the entry? The code answers it by
sniffing for key names, and getting it wrong has already produced two bugs --
three tables collapsed from five hundred entries to two, and a review gate that
matched nothing across ten tables. A record has no such question:

    Numbers:
    - params: {N: '389', c4: '112', c6: '-856'}
      number: '1.5185...'
      comment: ...

Named rather than positional, for about 6% more bytes. An identity built from
position is only as stable as an ordering nobody promised to keep: with two
parameters nested one way `1,2` means (a=1, b=2), and nested the other way it
still exists and means (a=2, b=1). Such a citation does not break, it resolves
and points at a different number, which is worse.

Naming also dissolves the grouped-parameter problem. Eleven tables declare
`group parameters` like `[['N'], ['c4', 'c6']]` and write one key `112, -856`
holding two values, so a property describing how a table should *look* decides
how its entries *parse*. Flattened, every parameter is named where it is used
and grouping goes back to being about presentation.

What this module does not do is decide the storage format. It converts in both
directions so the two forms can coexist while the corpus moves.
"""

from __future__ import annotations

#Keys that make a mapping an entry rather than another parameter level. The
#same set the renderer and the review gate use; they must agree about where
#the parameters stop, or one of them is walking a different table.
ENTRY_MARKERS = frozenset(['number', 'numbers', 'equals'])

#Where the flat form keeps an entry's parameter values.
PARAMS_KEY = 'params'


def parameter_groups(tree):
	"""The parameter names, grouped as the entries nest them.

	One group per nesting level. Normally one name each; the eleven tables
	with `group parameters` put two names in a level, and their keys hold two
	comma-separated values.
	"""
	if not isinstance(tree, dict):
		return []
	names = list((tree.get('Parameters') or {}).keys())
	display = tree.get('Display properties')
	if isinstance(display, dict):
		groups = display.get('group parameters')
		if isinstance(groups, list) and groups:
			return [list(g) if isinstance(g, list) else [g] for g in groups]
	return [[name] for name in names]


def split_key(key, group):
	"""Match one entry key against the names at its level.

	The stored key is written `112, -856` with a space and the identity is
	`112,-856` without one, so the values are stripped here; code that compares
	the two forms without normalising silently matches nothing.
	"""
	text = str(key)
	if len(group) == 1:
		return {group[0]: text.strip()}
	parts = [p.strip() for p in text.split(',')]
	#A key with the wrong number of parts is not something to guess at: pad
	#with None so the caller can see the shape is wrong rather than shifting
	#every later value into the wrong parameter.
	if len(parts) != len(group):
		parts = (parts + [None] * len(group))[:len(group)]
	return dict(zip(group, parts))


def to_records(tree):
	"""Every entry of ``tree`` as a flat record, in document order.

	A record is ``{params: {...}}`` plus whatever the entry said: `number`,
	and any annotation such as `comment`, `param-latex`, `proof`, `url`.

	Metadata sitting on a `numbers` container -- a `param-latex` covering a
	whole group -- is repeated onto each record inside it. That is a deliberate
	loss of structure rather than of information: the alternative is a shared
	block that reintroduces exactly the nesting ambiguity being removed.
	"""
	block = entries_block(tree)
	if block is None:
		return []

	groups = parameter_groups(tree)
	records = []

	def walk(node, params, depth, inherited):
		if isinstance(node, dict) and (set(node) & ENTRY_MARKERS):
			shared = {k: v for k, v in node.items()
			          if k not in ENTRY_MARKERS and k != PARAMS_KEY}
			container = node.get('numbers')
			if isinstance(container, dict):
				#A container of further entries at the *same* depth, sitting
				#beside metadata. Treating it as terminal is what collapsed
				#T33, T34 and T36 to two entries each.
				walk(container, params, depth, {**inherited, **shared})
				if 'number' not in node:
					return
			record = dict(inherited)
			record.update(shared)
			record[PARAMS_KEY] = dict(params)
			for marker in ('number', 'equals'):
				if marker in node:
					record[marker] = node[marker]
			records.append(record)
			return

		if isinstance(node, dict):
			group = groups[depth] if depth < len(groups) else ['param%d' % depth]
			for key, value in node.items():
				walk(value, {**params, **split_key(key, group)},
				     depth + 1, inherited)
			return

		#A bare value, or a list of them sharing one parameter value.
		record = dict(inherited)
		record[PARAMS_KEY] = dict(params)
		record['number'] = node
		records.append(record)

	if isinstance(block, list) and not groups:
		#A table with no parameters, such as Pi: a plain list of values.
		for item in block:
			walk(item, {}, 0, {})
	else:
		walk(block, {}, 0, {})
	return records


def to_nested(records, groups):
	"""Rebuild the nested form from records, for writing the export.

	Only as faithful as the flat form allows: metadata that was shared by a
	`numbers` container comes back repeated on each entry, since that is how
	the records carry it.
	"""
	#A table with no parameters is a plain list of values -- T67 holds 442 of
	#them, Pi holds one. There is nothing to key on, so the records are the
	#list; returning the first one and stopping loses the other 441.
	if not groups:
		out = []
		for record in records:
			rest = {k: v for k, v in record.items() if k != PARAMS_KEY}
			out.append(rest['number'] if set(rest) == {'number'} else rest)
		return out

	root = {}
	for record in records:
		params = record.get(PARAMS_KEY) or {}
		keys = []
		for group in groups:
			values = [params.get(name) for name in group]
			if any(v is None for v in values):
				break
			keys.append(','.join(str(v) for v in values))

		node = root
		for key in keys[:-1]:
			node = node.setdefault(key, {})

		rest = {k: v for k, v in record.items() if k != PARAMS_KEY}
		#A record carrying nothing but a value is written as that value, which
		#is what 54300 of the corpus's entries look like.
		if set(rest) == {'number'}:
			payload = rest['number']
		else:
			payload = rest

		if keys:
			node[keys[-1]] = payload
	return root


def entries_block(tree):
	"""The entries section, whichever of its two names it goes by."""
	if not isinstance(tree, dict):
		return None
	for name in ('Numbers', 'Data'):
		if name in tree:
			return tree[name]
	return None


def identity_of(record, groups):
	"""The citable identity of a record: its values, in nesting order.

	The same string the anchors and `?entry=` use, so a flattened table cites
	exactly as the nested one did.
	"""
	params = record.get(PARAMS_KEY) or {}
	parts = []
	for group in groups:
		for name in group:
			value = params.get(name)
			if value is None:
				return ','.join(parts)
			parts.append(str(value))
	return ','.join(parts)


def named_identity_of(record, groups):
	"""The identity that says which value is which: `a=1,b=2`.

	Unlike the positional form this survives somebody restructuring the
	nesting, which is the failure that resolves successfully and points at the
	wrong number.
	"""
	params = record.get(PARAMS_KEY) or {}
	parts = []
	for group in groups:
		for name in group:
			if params.get(name) is not None:
				parts.append('%s=%s' % (name, params[name]))
	return ','.join(parts)


def is_flat(block):
	"""Whether an entries block is written as records rather than nested.

	Decided by shape rather than by a flag on the table. A document that says
	what it is cannot disagree with a flag stored elsewhere, and a table being
	converted is then readable the moment it is written, with no second thing
	to keep in step.

	A parameterless table is also a list, so a list of plain values is not
	flat -- only a list whose items carry `params`.
	"""
	if not isinstance(block, list) or not block:
		return False
	return any(isinstance(item, dict) and PARAMS_KEY in item
	           for item in block)


def as_nested(tree):
	"""The tree with its entries nested, whichever form they arrived in.

	Applied where documents are loaded, so everything downstream -- the
	renderer, the number build, search, the review gate -- keeps working
	against one shape while the corpus moves table by table.
	"""
	if not isinstance(tree, dict):
		return tree
	for name in ('Numbers', 'Data'):
		block = tree.get(name)
		if is_flat(block):
			out = dict(tree)
			out[name] = to_nested(block, parameter_groups(tree))
			return out
	return tree
