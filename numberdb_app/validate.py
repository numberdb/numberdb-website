"""Checking a document before it becomes a table.

Three things could be saved that produce a table nobody would call correct, and
none of them failed visibly:

  * a made-up value type, accepted and stored;
  * an entry naming a parameter the table never declared, accepted and then
    indexed as no numbers at all, so the table showed the entry and answered no
    search containing it;
  * a structural key misspelt -- `numbr` for `number` -- which reached the
    number builder and came back as a Sage parse error on an error page.

What they have in common is that the document was well-formed and the result
looked ordinary. That is the failure this whole design keeps guarding against,
so it is worth catching where a person can still fix it.

**Structural keys are closed and annotation keys are open.** A document may use
`number`, `numbers`, `equals` and `params` to say what an entry *is*, and
nothing else may change how it is read; anything else on an entry is prose
about that entry. That openness is not an oversight, it is how the format has
been extended four times without anybody designing it -- `proof`, `url`, `both
signs` and even a misspelt `comments` all render because of it. So an unknown
key is a warning that suggests a correction rather than a refusal, unless it is
one character from a structural one, where guessing wrong is expensive.
"""

from __future__ import annotations

import difflib

__all__ = ['Problem', 'problems', 'check', 'DATA_TYPES', 'PARAMETER_TYPES']

#: What a table may say its values are. Every type in the corpus: 65 tables of
#: R, 16 of Z, 8 of Z[], 6 of Qp, 4 each of C and Q[], 3 of Q, and one `*R`.
DATA_TYPES = frozenset(['Z', 'Q', 'R', 'C', 'Qp', 'Z[]', 'Q[]', '*R'])

#: What a parameter may be. `Symbolic` is the second commonest, 27 declarations:
#: its values are names rather than numbers -- `Co1`, `unit-s`, `a_n/n!`.
PARAMETER_TYPES = frozenset(['Z', 'Q', 'R', 'C', 'Qp', 'Symbolic', 'Set'])

#: Keys that decide how an entry is read. Closed: adding one is a schema
#: change, because every reader has to implement it.
STRUCTURAL_KEYS = frozenset(['number', 'numbers', 'equals', 'params'])

#: Keys the corpus uses for prose about an entry. Not a permitted list -- an
#: unknown key still renders -- but enough to spell-check against.
KNOWN_ANNOTATIONS = frozenset(['comment', 'comments', 'param-latex', 'proof',
                               'url', 'both signs', 'reliability'])


class Problem:
	"""One thing wrong with a document.

	``fatal`` distinguishes what may not be saved from what is merely probably
	a mistake. A warning that blocks a save teaches people to work around the
	validator; a mistake that saves silently is what this exists to stop.
	"""

	__slots__ = ('message', 'fatal', 'where')

	def __init__(self, message, fatal=True, where=''):
		self.message = message
		self.fatal = fatal
		self.where = where

	def __repr__(self):
		return '<%s %s%s>' % ('error' if self.fatal else 'warning',
		                      self.message[:50],
		                      ' at %s' % (self.where,) if self.where else '')

	def __str__(self):
		return ('%s (at %s)' % (self.message, self.where) if self.where
		        else self.message)


def problems(tree):
	"""Everything wrong with ``tree``, fatal and otherwise."""
	found = []
	if not isinstance(tree, dict):
		return [Problem('A table must be a mapping of sections.')]

	found.extend(_check_types(tree))
	found.extend(_check_entries(tree))
	return found


def check(tree):
	"""Raise on anything fatal; return the warnings.

	Warnings come back for the caller to show, in the same way a soft size
	limit does: the document is saved and the author is told.
	"""
	from .editing import InvalidDocument

	found = problems(tree)
	fatal = [p for p in found if p.fatal]
	if fatal:
		raise InvalidDocument('; '.join(str(p) for p in fatal))
	return [p for p in found if not p.fatal]


def _check_types(tree):
	properties = tree.get('Data properties')
	if isinstance(properties, dict):
		declared = str(properties.get('type', '')).strip()
		if declared and declared not in DATA_TYPES:
			yield Problem(
				'%r is not a type this database knows. Use one of %s%s'
				% (declared, ', '.join(sorted(DATA_TYPES)),
				   _did_you_mean(declared, DATA_TYPES)),
				where='Data properties: type')

	parameters = tree.get('Parameters')
	if isinstance(parameters, dict):
		for name, spec in parameters.items():
			if not isinstance(spec, dict):
				continue
			declared = str(spec.get('type', '')).strip()
			if declared and declared not in PARAMETER_TYPES:
				yield Problem(
					'parameter %r is declared as %r, which is not a parameter '
					'type. Use one of %s%s'
					% (name, declared, ', '.join(sorted(PARAMETER_TYPES)),
					   _did_you_mean(declared, PARAMETER_TYPES)),
					where='Parameters: %s' % (name,))


def _check_entries(tree):
	from .flatten import entries_block, is_flat, parameter_groups

	block = entries_block(tree)
	if block is None:
		return

	declared = [name for group in parameter_groups(tree) for name in group]

	if is_flat(block):
		for index, record in enumerate(block):
			if not isinstance(record, dict):
				yield Problem('entry %d is not a record.' % (index,))
				continue
			yield from _check_record(record, index, declared)
		return

	#The nested form: the parameters are the nesting, so there is nothing to
	#cross-check there, but the entries themselves still have keys.
	for path, entry in _nested_entries(block):
		if isinstance(entry, dict):
			yield from _check_keys(entry, 'entry %s' % (path,))


def _check_record(record, index, declared):
	where = 'entry %d' % (index,)
	params = record.get('params')

	if params is None:
		yield Problem('%s has no params.' % (where,), where=where)
	elif not isinstance(params, dict):
		yield Problem('%s has params that are not a mapping.' % (where,),
		              where=where)
	elif declared:
		named = set(params)
		expected = set(declared)
		for extra in sorted(named - expected):
			#The case that saved happily and then indexed nothing: the table
			#showed the entry and no search containing it found anything.
			yield Problem(
				'%s names a parameter %r that the table does not declare. '
				'Declared: %s%s'
				% (where, extra, ', '.join(declared),
				   _did_you_mean(extra, expected)),
				where=where)
		for missing in sorted(expected - named):
			#A warning, not a refusal. Seven entries in the corpus are like
			#this and every one is a statement about a *family* rather than a
			#value -- `alpha: 1/2` carrying `equals: HREF{Legendre_polynomials}`
			#and no `n`, because the claim is about every n at once. They want
			#to become a table-level relation rather than an entry, and until
			#they do, refusing them would make six tables uneditable.
			yield Problem(
				'%s does not give the parameter %r. An entry with only some of '
				'the parameters is a statement about a family rather than one '
				'value, and its identity is correspondingly incomplete.'
				% (where, missing), fatal=False, where=where)

	if 'number' not in record and 'equals' not in record:
		yield Problem('%s has neither a number nor an equals.' % (where,),
		              where=where)
	elif 'number' not in record:
		#`equals` without a value points at another table's entry. Fine, and
		#worth noticing: it is a row in a table of numbers that holds none.
		yield Problem(
			'%s has no number of its own, only a reference to another entry.'
			% (where,), fatal=False, where=where)

	yield from _check_keys(record, where)


def _check_keys(entry, where):
	"""Spell-check an entry's keys against the ones that mean something."""
	for key in entry:
		if key in STRUCTURAL_KEYS or key in KNOWN_ANNOTATIONS:
			continue
		near = difflib.get_close_matches(str(key), STRUCTURAL_KEYS, n=1,
		                                 cutoff=0.8)
		if near:
			#One character from a structural key. Guessing wrong here is
			#expensive: `numbr` is not prose about the entry, it is a value
			#that will not be stored and will not be searchable.
			yield Problem(
				'%s has a key %r. Did you mean %r? A misspelt %r is not '
				'stored as a value and the entry answers no search.'
				% (where, key, near[0], near[0]), where=where)
			continue
		near = difflib.get_close_matches(str(key), KNOWN_ANNOTATIONS, n=1,
		                                 cutoff=0.85)
		if near:
			yield Problem(
				'%s has a key %r; did you mean %r? It is kept and shown either '
				'way.' % (where, key, near[0]), fatal=False, where=where)


def _nested_entries(node, path=()):
	"""Walk the nested form, yielding (path, entry) for each entry."""
	if isinstance(node, dict):
		if set(node) & STRUCTURAL_KEYS:
			inner = node.get('numbers')
			if isinstance(inner, dict):
				yield from _nested_entries(inner, path)
				return
			yield ','.join(path), node
			return
		for key, value in node.items():
			yield from _nested_entries(value, path + (str(key),))
		return
	if isinstance(node, list):
		for item in node:
			if isinstance(item, dict):
				yield ','.join(path), item


def _did_you_mean(value, candidates):
	"""Suggest the nearest permitted spelling, ignoring case.

	`QP` and `Qp` differ in one character of two, which scores below any
	sensible similarity cutoff while being obviously the same intention. Case
	is exactly what somebody gets wrong about `Qp`, `Z[]` and `Symbolic`, so
	it is normalised away before comparing and the suggestion is offered in its
	correct spelling.
	"""
	options = {str(c).lower(): c for c in candidates}
	near = difflib.get_close_matches(str(value).lower(), sorted(options), n=1,
	                                 cutoff=0.6)
	return '. Did you mean %r?' % (options[near[0]],) if near else '.'
