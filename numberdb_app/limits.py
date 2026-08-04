"""How big a table may reasonably get, and what to do when it wants to be bigger.

A table is a reference, not a dump. A number found among a million
machine-generated values says almost nothing about itself -- it lies in an
equally-spaced grid, and so does every other real number nearby -- whereas a
number found among forty-five thousand hand-curated ones at a hundred digits is
a genuine identification. The limits here exist to protect that property, which
is the whole worth of the database, and not to save disk.

They are therefore *editorial*, and the numbers are not invented: they come from
what the corpus already does. Measured over all 107 resolved tables in August
2026:

    entries per table   median 119, p75 exactly 1000, max 1135
    digits per value    median exactly 100, p90 124, p95 202, max 1019
    entries block       median 56 KB, p95 221 KB, max 236 KB

The digit figures are for tables of approximations. Tables of exact values are
excluded from that limit entirely -- see :func:`stores_exact_values` -- because
a polynomial or an integer has no precision to choose.

A median of exactly 100 and a p75 of exactly 1000 are not what a natural
distribution looks like; they are a house style that was already being kept.
So those two numbers are what we *recommend*, and they are not what we enforce
-- 26 tables sit just above 1000 entries and 31 write more than 100 digits, all
of them deliberately. A threshold that fires on a quarter of the corpus teaches
everyone to ignore it.

The enforced soft limits sit where the tail actually begins, so that being over
one is unusual enough to be worth a sentence of explanation: 1200 entries and
256 KB flag nothing that exists today, and 500 digits flags four tables, which
are exactly the "these digits were expensive" cases that ought to say so.

That phrase is the whole test for precision. A value cheap to evaluate needs no
more than the hundred digits that identify it, because a reader who wants more
can compute them; a value that took CPU-months is worth recording to whatever
precision was reached, since nobody else will be repeating the calculation.

The block limit is a threshold on a *serialisation*, so it moves when the
serialisation does. Flat records with named parameters cost about 27% more than
the nested form -- 6.8 MB against 8.7 MB across the corpus -- and leaving the
limit at the 256 KB that fitted the nested form would have flagged T66, T69,
T70 and T74 for growing, when not one of them had changed. 320 KB restores the
property the number is chosen for: nothing that exists today is over it, the
largest flat block being 271 KB.

Three limits rather than two, because the first two trade off against each
other. Few numbers known to great precision is as legitimate as many numbers
known to a hundred digits -- what is not legitimate is both at once, and only a
limit on the whole block can say that. 1000 entries at 100 digits is about
100 KB; 200 entries at 1000 digits is about 200 KB; both together would be a
megabyte, and the block limit admits either one and refuses the pair.

Hard limits sit far above and mean something different. A soft limit is a
judgement about what makes a good table and can be overridden by someone who
explains why. A hard limit is not a judgement at all: it is the point where a
paste went wrong, or where the editor and the diff view stop working, and no
reason makes it a good idea.
"""

from __future__ import annotations

import re

#: House style, shown as advice while editing. Nothing is checked against
#: these; they describe what a typical table looks like.
#:
#: A hundred digits is the recommendation whenever a hundred digits is easy to
#: get, and the reason is not storage. Digits that are cheap to compute carry
#: no information: anybody who wants the thousandth digit of a value that takes
#: a second to evaluate can have it, and writing it down here adds nothing a
#: reader could not produce themselves. A hundred is far more than enough to
#: identify a number, which is what this database is for. Extra digits earn
#: their place only when they were expensive to obtain -- which is exactly the
#: reason a table is expected to state when it goes over the soft limit below.
RECOMMENDED_ENTRY_COUNT = 1000
RECOMMENDED_DIGITS = 100

#: Over one of these, a table must say why. Chosen so that being over is rare
#: rather than routine -- see the module docstring.
SOFT_ENTRY_COUNT = 1200
SOFT_DIGITS = 500
SOFT_BLOCK_BYTES = 320 * 1024

#: What no table may exceed, reason or not.
HARD_ENTRY_COUNT = 50_000
HARD_DIGITS = 10_000
HARD_BLOCK_BYTES = 4 * 1024 * 1024

#: Where an author states why a table is over a soft limit. Free prose: the
#: point is that a person reviewing it can judge the reason, not that a machine
#: can parse it.
EXCEPTION_KEY = 'Size exception'


class TooBig(Exception):
	"""A limit was exceeded and nothing was written.

	Always a hard limit for an edit made on the site, where a soft limit is a
	warning rather than a refusal. Also a soft limit for a writer that cannot
	be warned -- see :func:`enforce`.
	"""

	def __init__(self, breaches):
		self.breaches = list(breaches)
		super().__init__('; '.join(b.message for b in self.breaches))


class Breach:
	"""One limit, exceeded, and by how much."""

	def __init__(self, kind, actual, limit, message, hard=False):
		self.kind = kind
		self.actual = actual
		self.limit = limit
		self.message = message
		self.hard = hard

	def __repr__(self):
		return '<Breach %s %s/%s>' % (self.kind, self.actual, self.limit)


def _digits(text):
	"""How many digits a value actually writes down.

	Counting digit characters rather than parsing: the corpus holds decimals,
	rationals, p-adics and polynomials, and "how much was written" is the
	quantity the limit is about in every one of those cases.
	"""
	return len(re.sub(r'[^0-9]', '', str(text)))


def _values_of(entry):
	"""Every value written down in one entry, list forms included."""
	if isinstance(entry, str):
		return [entry]
	if isinstance(entry, list):
		out = []
		for item in entry:
			out.extend(_values_of(item))
		return out
	if isinstance(entry, dict):
		return _values_of(entry.get('number', []))
	return []


#: What the entries section may be called. `Numbers` in 97 tables and `Data` in
#: 10; the normalisation to a single spelling has been done in the data
#: repository but not everywhere in the database, and a measurement that looked
#: only for `Numbers` would score those ten as empty and never check them.
ENTRIES_SECTIONS = ('Numbers', 'Data')


def entries_block(tree):
	"""The section holding the entries, whichever of its names it goes by."""
	if not isinstance(tree, dict):
		return None
	for name in ENTRIES_SECTIONS:
		if name in tree:
			return tree[name]
	return None


def measure(tree):
	"""The three numbers a table is judged on."""
	import yaml

	from .review import flatten_entries

	block = entries_block(tree)
	if block is None:
		return {'entries': 0, 'digits': 0, 'bytes': 0}

	#The same walk the review gate uses. Two walkers over this corpus would
	#eventually disagree, and the disagreement would be silent: a table would
	#be inside the limit by one count and outside it by the other.
	entries = flatten_entries(block)
	values = [v for entry in entries.values() for v in _values_of(entry)]
	return {
		'entries': len(entries),
		'digits': max((_digits(v) for v in values), default=0),
		'bytes': len(yaml.dump(block, default_flow_style=False,
		                       allow_unicode=True).encode('utf-8')),
	}


def stated_reason(tree):
	"""The author's explanation for going over, if they gave one."""
	if not isinstance(tree, dict):
		return ''
	for section in (tree, tree.get('Data properties') or {}):
		if isinstance(section, dict):
			value = section.get(EXCEPTION_KEY)
			if isinstance(value, str) and value.strip():
				return value.strip()
	return ''


#: Declared types whose values are written out in full rather than to a chosen
#: precision. Across the corpus: Z (16 tables), Q (3), Z[] (8), Q[] (4).
EXACT_TYPES = frozenset(['Z', 'Q', 'Z[]', 'Q[]'])


def stores_exact_values(tree):
	"""Whether this table's values are exact objects rather than approximations.

	The digit limit is about *precision*, and an exact value has none to
	choose. T96 holds modular polynomials for the j-invariant, and its longest
	entry writes 54342 digits: that is the coefficients of a polynomial, not a
	real number expanded to 54342 places. Writing fewer would not make it less
	precise, it would make it a different polynomial, and wrong.

	The same goes for an integer or a rational: how long it is, is a fact about
	the number. What still applies to these tables is the limit on the whole
	entries block, which is the right backstop -- it catches a table that is
	genuinely too large without pretending that an exact value was written to
	too many places.

	It also does the editorial work by itself. A very long polynomial is
	usually not interesting enough to record, and T96 holds only twelve for
	exactly that reason; at 129 KB it has room for one or two more before the
	block limit asks whether the next one is worth its size. That is a better
	rule than "polynomials must be short", because it lets the table grow while
	the entries are small and pushes back precisely when they are not.
	"""
	if not isinstance(tree, dict):
		return False
	props = tree.get('Data properties')
	if not isinstance(props, dict):
		return False
	return str(props.get('type', '')).strip() in EXACT_TYPES


def claims_completeness(tree):
	"""Whether the table says it holds every member of its family.

	This exempts it from the entry-count limit with no reason required, and
	that is not a courtesy: truncating a complete table does not make it
	smaller, it makes it *wrong*. A reader who is told a table is complete and
	finds it cut off at a round number has been misled about the mathematics.
	"""
	if not isinstance(tree, dict):
		return False
	props = tree.get('Data properties')
	if not isinstance(props, dict):
		return False
	value = props.get('complete')
	#The corpus writes `no`/`yes` as words, read with BaseLoader, so this is a
	#string comparison rather than a truth test.
	return str(value).strip().lower() in ('yes', 'true', 'complete')


def check(tree):
	"""Every limit this tree exceeds, hard ones included.

	Returns a list of :class:`Breach`. An empty list means the table is within
	everything, which is true of 103 of the 107 tables in the corpus; the four
	that are not are the deep-precision ones, and they should each carry a
	sentence saying why.
	"""
	size = measure(tree)
	complete = claims_completeness(tree)
	breaches = []

	def note(kind, actual, soft, hard, unit, what):
		if actual > hard:
			breaches.append(Breach(
				kind, actual, hard, hard=True,
				message='%s is %s %s, above the hard limit of %s'
				        % (what, actual, unit, hard)))
		elif actual > soft:
			breaches.append(Breach(
				kind, actual, soft,
				message='%s is %s %s, above the usual limit of %s'
				        % (what, actual, unit, soft)))

	if not complete:
		note('entries', size['entries'], SOFT_ENTRY_COUNT, HARD_ENTRY_COUNT,
		     'entries', 'this table holds')
	elif size['entries'] > HARD_ENTRY_COUNT:
		#Completeness excuses an editorial judgement, never a hard ceiling.
		breaches.append(Breach(
			'entries', size['entries'], HARD_ENTRY_COUNT, hard=True,
			message='this table holds %s entries, above the hard limit of %s'
			        % (size['entries'], HARD_ENTRY_COUNT)))

	if not stores_exact_values(tree):
		note('digits', size['digits'], SOFT_DIGITS, HARD_DIGITS, 'digits',
		     'the longest value writes')
	note('bytes', size['bytes'], SOFT_BLOCK_BYTES, HARD_BLOCK_BYTES, 'bytes',
	     'the entries block is')
	return breaches


def enforce(tree, strict=False):
	"""Apply the limits at commit time; return the soft breaches to report.

	Hard limits always raise. Soft limits are a conversation: a person editing
	on the site is warned and their edit is still saved, because they may well
	have a good reason and the review queue is where reasons get judged.

	``strict`` is for writers that cannot be talked to -- the API, and bulk
	machine proposals. A script has no judgement to exercise, so it must
	declare the reason in the document itself before it is allowed over a soft
	limit. This is the main thing standing between "programmatic editing" and
	"the corpus fills up with unconsidered rows".
	"""
	breaches = check(tree)
	hard = [b for b in breaches if b.hard]
	if hard:
		raise TooBig(hard)

	soft = [b for b in breaches if not b.hard]
	if soft and stated_reason(tree):
		return []
	if soft and strict:
		raise TooBig(soft)
	return soft
