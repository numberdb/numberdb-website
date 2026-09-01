"""Number search: which stored values could be the one being looked for.

Two questions are easy to confuse. The stored value is an exact number that is
only *known* to lie in an interval, so a hit means "the query interval and the
stored interval could describe the same number" -- they overlap. The previous
query asked instead whether the stored interval sat *inside* the query, which
answers a different question and quietly loses the coarsely-known values: a
number stored to three digits can never sit inside a query given to ten, so
searching for pi to ten places would not find pi stored to three.

Overlap is the correct test but cannot be served by the two btree indexes on
the float bounds -- as a pair of unbounded half-ranges it degrades to a
sequential scan. It is served instead by a GiST index over ``value_range``.

Results are ranked by how much of the stored interval the query accounts for,

    score = |Q intersect S| / |S|

so a value pinned down inside the query outranks one that merely brushes it.
The score is capped at 1, which is what makes the fast path below sound.

All three kinds share that shape -- ask the symmetric question, rank by the
same score, stop once a page of perfect matches exists -- but need different
machinery to answer it. Reals need a stored range and a GiST index; complex
boxes are four indexed comparisons; p-adics need no index work at all, because
in an ultrametric space balls nest instead of overlapping and the question
collapses to string prefixes.
"""

from decimal import Decimal

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.backends.postgresql.psycopg_any import NumericRange
from django.db.models import F, Q
from django.db.models.expressions import RawSQL

from .models import Number, NumberComplex, NumberPAdic, searchable_range

__all__ = ['one_per_table', 'search_real_numbers', 'search_fractional_parts',
           'search_complex_numbers', 'search_p_adic_numbers',
           'real_query_range', 'full_text_query', 'search_metadata',
           'METADATA_LIMIT', 'MIN_RANK']

#Scored in SQL so that ordering can happen before LIMIT; scoring in Python
#would mean fetching every overlapping row first.
#
#`*` is range intersection, and the rows are already filtered to overlap, so
#the intersection is never empty. The two special cases are real:
#
#  - an exactly-known value has a zero-width range, so the ratio would be 0/0.
#    It overlaps only if it lies in the query, and then the query accounts for
#    all of it, which is a score of 1.
#  - a saturated value has an unbounded end and infinite width, so no finite
#    query can account for a meaningful share of it. It scores 0 and sorts
#    last, which keeps it findable without letting it displace real answers.
_SCORE_SQL_TEMPLATE = """
CASE
	WHEN lower_inf("db_number"."value_range")
	  OR upper_inf("db_number"."value_range") THEN 0
	WHEN upper("db_number"."value_range")
	   = lower("db_number"."value_range") THEN 1
	ELSE (upper("db_number"."value_range" * %s)
	    - lower("db_number"."value_range" * %s))
	   / (upper("db_number"."value_range")
	    - lower("db_number"."value_range"))
END
"""

_SCORE_SQL = _SCORE_SQL_TEMPLATE
_FRAC_SCORE_SQL = _SCORE_SQL_TEMPLATE.replace('value_range', 'frac_range')


#: How weakly a value may be known and still be worth returning for a number.
#: A value known to worse than this cannot identify anything: matching it says
#: a wide range overlaps another wide range, and it would say that for every
#: experimental value in the range.
#:
#: The corpus is insensitive to the exact figure -- 1e-4 and 1e-5 both exclude
#: the same 16 rows of 45832 -- so this is not a knife edge. What it decides is
#: which side the measured physical constants fall on:
#:
#:     1e-3   excludes the 7 merely-bounded values only
#:            (Ramsey numbers, the matrix multiplication exponent)
#:     1e-5   also excludes the 9 mass ratios, e.g. 0.88153(17)
#:
#: Read from settings so it can be moved without a code change, and without a
#: rebuild: it is applied to a stored measurement at query time. Whatever it is
#: set to, the tables mark the values it excludes.
def max_relative_width():
	from django.conf import settings
	return getattr(settings, 'NUMBERDB_MAX_RELATIVE_WIDTH', 1e-5)


def _reviewed(queryset):
	"""Only values whose current content has been reviewed, on a public table.

	A draft's values are excluded here rather than by never indexing them, so
	that publishing is one flag and not a rebuild.
	

	Separate from :func:`_identifiable` because the other three kinds have no
	relative width to judge: a p-adic ball, a complex box and a polynomial are
	either right or wrong, not imprecise. The review gate applies to all four.
	"""
	return queryset.filter(reviewed = True, table__published = True)


def _identifiable(queryset):
	"""Drop values that cannot answer the question search by number asks.

	Two reasons, and both are about the same asymmetry. A reader looking at a
	table page can see that an entry is imprecise or unreviewed and weigh it;
	somebody typing digits into the search box cannot, and a wrong fortieth
	digit looks exactly like a right one.

	So this excludes values known too weakly to identify anything, and values
	whose current content nobody has reviewed. Both stay visible on their table
	and both are marked there.

	A null width means exact_text could not be parsed, which is no reason to
	hide the row; those are kept.
	"""
	return queryset.filter(
		Q(exact_relative_width__lte = max_relative_width())
		| Q(exact_relative_width__isnull = True)
	).filter(reviewed = True, table__published = True)


def real_query_range(r_query):
	"""A Sage real interval as the numrange to search with."""
	return searchable_range(r_query.lower(), r_query.upper())


def one_per_table(queryset, limit, order=()):
	"""The best row from each table, and how many that table holds.

	Search answers "I have this number, what is it", and the answer wanted is
	the list of *contexts* it appears in. A value that occurs many times in one
	table -- `x` is a Chebyshev polynomial three times over, and a Fibonacci
	one, and a Legendre one -- would otherwise fill the page with one table's
	rows and crowd out every other answer, which is the opposite of what the
	reader asked.

	So the limit counts tables. Each returned row carries
	`occurrences_in_table`, because "and 3 more here" is itself informative:
	it says the value is characteristic of that family rather than incidental.

	`DISTINCT ON` needs the distinct column to lead the ordering, so the caller
	passes the ranking that should decide *which* row represents a table, and
	sorts the result afterwards if the page order matters.
	"""
	from django.db.models import Count

	counts = dict(queryset.values_list('table_id').annotate(n=Count('id')))
	rows = list(queryset.order_by('table_id', *order).distinct('table_id')[:limit])
	for row in rows:
		row.occurrences_in_table = counts.get(row.table_id, 1)
	return rows


def search_real_numbers(r_query, limit):
	"""Stored values that could be ``r_query``, best first.

	Broad queries are answered without sorting anything. A stored interval
	lying entirely inside the query scores exactly 1, and 1 is the maximum, so
	once ``limit`` of them are found no unexamined row can outrank any of them
	-- the ranking is already settled and the rest of the table is irrelevant.
	Postgres pushes the LIMIT into the scan and stops there, so the cost stops
	following the number of matches: a query matching 20094 stored values is
	answered in 0.56 ms rather than the 22.8 ms that scoring them all costs.

	The order within that set is arbitrary, which is the deliberate trade. They
	are all equally good answers by the ranking, and for a query this broad the
	useful next step is a narrower query rather than a better-sorted page.

	When fewer than ``limit`` are contained the query is a precise one, the
	overlapping set is correspondingly small, and it is scored and sorted in
	full -- measured at 0.54 ms, so the fast path never costs anything when it
	does not apply.
	"""
	query = real_query_range(r_query)

	contained = one_per_table(
		_identifiable(Number.objects).filter(value_range__contained_by = query),
		limit)
	if len(contained) >= limit:
		return contained

	#Fewer than a full page score 1, so the coarser values that merely overlap
	#have to be ranked in. This re-finds the contained ones -- they overlap
	#too -- and sorts the union, so the result is a superset of the above.
	rows = one_per_table(
		_identifiable(Number.objects)
			.filter(value_range__overlap = query)
			.annotate(overlap_score = RawSQL(_SCORE_SQL, (query, query))),
		limit, order=('-overlap_score',))
	#`DISTINCT ON` had to order by table to pick each table's best row; the
	#page wants them best-first.
	return sorted(rows, key=lambda row: -row.overlap_score)


#Per axis rather than by area, so that a value exact in one component and
#interval-valued in the other still scores. A zero-width axis contributes 1:
#it is a point, and the row is only here because it overlaps, so the query
#accounts for all of that axis. A saturated axis has infinite width and
#divides to 0, which sorts it last without dropping it.
_COMPLEX_SCORE_SQL = """
(CASE WHEN "db_numbercomplex"."re_upper" = "db_numbercomplex"."re_lower" THEN 1
      ELSE greatest(0, least("db_numbercomplex"."re_upper", %s)
                     - greatest("db_numbercomplex"."re_lower", %s))
         / ("db_numbercomplex"."re_upper" - "db_numbercomplex"."re_lower") END)
*
(CASE WHEN "db_numbercomplex"."im_upper" = "db_numbercomplex"."im_lower" THEN 1
      ELSE greatest(0, least("db_numbercomplex"."im_upper", %s)
                     - greatest("db_numbercomplex"."im_lower", %s))
         / ("db_numbercomplex"."im_upper" - "db_numbercomplex"."im_lower") END)
"""


def search_complex_numbers(n_query, limit):
	"""Stored complex values that could be ``n_query``, best first.

	The same shape as the real case, one dimension up: a stored box lying
	entirely inside the query box is as good a match as can exist, so once
	``limit`` of them are found the ranking cannot be improved and the rest of
	the table need not be looked at.

	Containment is four comparisons on the four indexed float columns, which
	Postgres combines into a BitmapAnd, so the fast path does not need the
	box-and-GiST treatment the reals got. At 1849 rows even the scored fallback
	is a sequential scan costing a fifth of a millisecond; if this table grows
	by orders of magnitude, that fallback is what to index.
	"""
	re_low, re_high = float(n_query.real().lower()), float(n_query.real().upper())
	im_low, im_high = float(n_query.imag().lower()), float(n_query.imag().upper())

	contained = one_per_table(
		_reviewed(NumberComplex.objects).filter(
			re_lower__gte = re_low, re_upper__lte = re_high,
			im_lower__gte = im_low, im_upper__lte = im_high,
		), limit)
	if len(contained) >= limit:
		return contained

	rows = one_per_table(
		_reviewed(NumberComplex.objects)
			.filter(
				re_lower__lte = re_high, re_upper__gte = re_low,
				im_lower__lte = im_high, im_upper__gte = im_low,
			)
			.annotate(overlap_score = RawSQL(
				_COMPLEX_SCORE_SQL, (re_high, re_low, im_high, im_low))),
		limit, order=('-overlap_score',))
	return sorted(rows, key=lambda row: -row.overlap_score)


def _coarser_ball_strings(number_string):
	"""The stored strings whose ball would contain this query's ball.

	Q_p is ultrametric, so two balls are either disjoint or one contains the
	other -- they cannot partially overlap the way real intervals do. A ball is
	written "<prime>,<valuation>,<d0>|<d1>|..." with the digits least
	significant first, so dropping trailing digits widens the ball and every
	ball containing this one is a prefix of this string. That makes the set
	finite and small: at most one entry per digit, which is where the whole
	problem collapses to a list of equality lookups on an index that already
	exists, with no range type and no GiST.

	Cut only at '|' boundaries. Digits are zero-padded to a fixed width, so for
	p >= 11 they are multi-character and a careless prefix would split one.

	The full string is excluded: those are the values at least as precise as the
	query, which the containment query already finds.
	"""
	prime, valuation, digits = number_string.split(',', 2)
	places = digits.split('|')
	return ['%s,%s,%s' % (prime, valuation, '|'.join(places[:count]))
	        for count in range(1, len(places))]


def search_p_adic_numbers(number_string, limit):
	"""Stored p-adic values that could be the query, best first.

	Both directions, where before only one was asked. A stored value more
	precise than the query lies inside it and its string starts with the
	query's; a stored value *less* precise contains the query and its string is
	a prefix of the query's. Only the first was searched, so a query more
	precise than the stored value found nothing -- the same asymmetry the reals
	had, and the reason the callers used to have to blunt the query's precision
	before searching.

	Ranking needs no SQL here. For nested balls the score reduces to
	p**-(query precision - stored precision), which is monotonic in the stored
	precision, so ordering by score is ordering by string length: exact matches
	and finer values first, then the coarser ones, widest last.
	"""
	inside = one_per_table(
		_reviewed(NumberPAdic.objects).filter(
			number_string__startswith = number_string), limit)
	if len(inside) >= limit:
		return inside

	shown = {row.table_id for row in inside}
	coarser = [row for row in one_per_table(
		_reviewed(NumberPAdic.objects).filter(
			number_string__in = _coarser_ball_strings(number_string)), limit)
		if row.table_id not in shown]
	coarser.sort(key = lambda number: -len(number.number_string))
	return (inside + coarser)[:limit]


def search_fractional_parts(f_query, limit):
	"""Stored values whose fractional part could be ``f_query``, best first.

	The real search, applied to the other range column. It was the last place
	still asking for containment, and it had the same consequence: a fractional
	part known to three digits cannot sit inside a query given to ten, so a
	precise query never returned it. 39344 of the 45832 stored fractional parts
	are interval-valued.

	Values whose fractional part is entirely unknown are excluded. When a
	number's own interval straddles an integer, frac() gives [0,1] -- 715 rows
	say only "somewhere in the unit interval". Those overlap every query, so
	admitting them turns a precise search into 720 results of which 715 carry no
	information about the fractional part at all, burying the 5 that do.

	This is the one place where overlap needs qualifying. Elsewhere a wide
	stored interval is a weak match and the score demotes it; here it is not a
	weak match but the absence of a measurement, and the two should not be
	ranked on the same scale. The saturated reals do not have this problem: an
	unbounded range sits out at 1e308 and does not reach an ordinary query.
	"""
	query = real_query_range(f_query)
	unknown = NumericRange(Decimal(0), Decimal(1), '[]')

	contained = one_per_table(
		_identifiable(Number.objects).filter(frac_range__contained_by = query),
		limit)
	if len(contained) >= limit:
		return contained

	rows = one_per_table(
		_identifiable(Number.objects)
			.filter(frac_range__overlap = query)
			.exclude(frac_range__contains = unknown)
			.annotate(overlap_score = RawSQL(_FRAC_SCORE_SQL, (query, query))),
		limit, order=('-overlap_score',))
	return sorted(rows, key=lambda row: -row.overlap_score)


#: Results shown on one page of the panel. The searches themselves cap here
#: too, so a query matching twenty thousand values costs the same as one
#: matching ten -- see search_real_numbers.
PAGE_SIZE = 100


def search_by_term(term, limit = PAGE_SIZE):
	"""Everything matching a typed search term, best first.

	The panel under the search bar renders this. It asks the same questions the
	dropdown does, but keeps the answers rather than the first ten, because a
	query can match thousands and a dropdown cannot say so.

	A term is offered to every parser that might accept it, and each that does
	contributes its matches: "0.5" is a real, and also a fractional part, and
	the asker may have meant either. Results are grouped by what the term was
	read as, so the page can say which question it answered.

	Returns a list of {kind, label, numbers} groups. Empty groups are dropped,
	so an empty list means nothing matched anything.
	"""
	from utils.utils import (blur_complex_interval, blur_real_interval,
	                         parse_complex_interval, parse_fractional_part,
	                         parse_p_adic, parse_polynomial,
	                         parse_real_interval)
	from .models import NumberPAdic, Polynomial

	term = (term or '').strip()
	if not term:
		return []

	groups = []

	def add(kind, label, numbers):
		if numbers:
			groups.append({'kind': kind, 'label': label, 'numbers': list(numbers)})

	#Each parser is tried independently and may raise on input meant for
	#another: parse_polynomial on "3.14" and parse_p_adic on a decimal both
	#reject rather than return None in some cases.
	def attempt(parse, search):
		try:
			parsed = parse(term)
		except Exception:
			return None
		if parsed is None:
			return None
		try:
			return search(parsed)
		except Exception:
			return None

	add('real', 'Real numbers',
	    attempt(parse_real_interval,
	            lambda r: search_real_numbers(blur_real_interval(r), limit)))

	add('complex', 'Complex numbers',
	    attempt(parse_complex_interval,
	            lambda n: search_complex_numbers(blur_complex_interval(n), limit))
	    if 'i' in term.lower().replace('j', 'i') else None)

	add('p-adic', 'p-adic numbers',
	    attempt(parse_p_adic,
	            lambda n: search_p_adic_numbers(
	                NumberPAdic(sage_number=n).number_string, limit)))

	add('fractional-part', 'Numbers with this fractional part',
	    attempt(parse_fractional_part,
	            lambda f: search_fractional_parts(blur_real_interval(f), limit)))

	def _polynomials(p):
		if p.number_of_terms() < 2:
			return None
		polynomial = Polynomial(sage_polynomial=p)
		return _reviewed(Polynomial.objects).filter(
			number_string_hash=polynomial.number_string_hash,
			number_string=polynomial.number_string)[:limit]

	add('polynomial', 'Polynomials', attempt(parse_polynomial, _polynomials))

	return groups


def search_number(value, limit = PAGE_SIZE):
	"""Search for a number the caller already has.

	The counterpart to search_by_term, one level lower: the caller supplies a
	value rather than text to be parsed, or an expression to be evaluated. It
	is the cheap path and should be the usual one -- searching this way costs a
	parse and an indexed query, where /api/search forks a sandboxed Sage
	process to compute a number the caller was already holding.

	``value`` is a Sage object. Dispatch is on its parent, never on whatever
	attributes it happens to expose: Sage polynomials and p-adics both carry
	numerator() and denominator(), so anything that sniffed for those would
	take them for rationals.
	"""
	from sage.rings.all import RIF, CIF, ZZ, QQ
	from utils.utils import (blur_complex_interval, blur_real_interval,
	                         is_pAdicField, is_polynomial_ring)
	from .models import NumberPAdic, Polynomial

	parent = value.parent()

	if is_pAdicField(parent):
		return search_p_adic_numbers(
			NumberPAdic(sage_number = value).number_string, limit)

	if is_polynomial_ring(parent):
		#No identifiability filter: a polynomial is exact, so there is no
		#question of it being known too weakly to identify anything.
		polynomial = Polynomial(sage_polynomial = value)
		return one_per_table(_reviewed(Polynomial.objects).filter(
			number_string_hash = polynomial.number_string_hash,
			number_string = polynomial.number_string), limit)

	if parent is CIF or parent == CIF:
		return search_complex_numbers(blur_complex_interval(value), limit)

	#Exact values are searched as point intervals on the real line, which is
	#what the evaluator path does with them too.
	if parent in (ZZ, QQ):
		value = RIF(value)
		parent = value.parent()

	if parent is RIF or parent == RIF:
		return search_real_numbers(blur_real_interval(value), limit)

	raise ValueError('no search for values of %s' % (parent,))


#: Tables or tags returned for one term. The dropdown asks for fewer, because
#: it shares ten rows with the numbers; a submitted search has room to show
#: what matched.
METADATA_LIMIT = 20

#: Below this rank a match is noise -- a term sharing a stem with a word buried
#: in a table's comments. Kept identical to what the dropdown has always used,
#: so the two agree about what counts as a match.
MIN_RANK = 0.01


def full_text_query(term):
	"""A term as a Postgres query: earlier words in full, the last as a prefix.

	The last word is a prefix because the dropdown runs while the user is
	typing and "multiplicat" should already find "multiplication". A submitted
	search inherits it, which costs nothing -- a complete word is a prefix of
	itself -- and keeps one implementation rather than two that drift.

	Truncated to six characters for the same reason it always was: a prefix
	index is only selective for so long, and beyond that the query grows
	without matching anything more.
	"""
	words = [word for word in (term or '').split(' ') if word]
	if not words:
		return None

	#Every word quoted, and a quote inside one doubled, so that a term cannot
	#be read as tsquery syntax. The old spelling interpolated words bare, which
	#made "d'Alembert" a raw query with an unbalanced quote in it.
	def quoted(word):
		return "'%s'" % (word.replace("'", "''"),)

	#The prefix is asked for twice, stemmed and unstemmed, because neither
	#alone is right.
	#
	#Stemmed alone loses words the stemmer rewrites when they are cut short:
	#"Chebyshev" truncated to "chebys" stems to "chebi" -- the rule that takes
	#"bodies" to "bodi" -- and "chebi" is not a prefix of the indexed
	#"chebyshev", so the search bar found nothing for it while finding
	#"Cyclotomic" perfectly well, since "cyclot" survives untouched.
	#
	#Unstemmed alone loses the opposite case: the vector holds "polynomi" for
	#"polynomials", and a plain "polynomials" prefix never reaches it.
	#
	#Either match is a match, so both are asked and the results are OR-ed.
	#The truncation is kept for the unstemmed half, where it is what makes the
	#dropdown work while somebody is still typing, and dropped from the
	#stemmed half, where it was doing the damage.
	last = words[-1]
	prefix = (SearchQuery('%s:*' % (quoted(last),), search_type='raw')
	          | SearchQuery('%s:*' % (quoted(last[:6]),), search_type='raw',
	                        config='simple'))
	if len(words) == 1:
		return prefix
	earlier = ' & '.join(quoted(word) for word in words[:-1])
	return SearchQuery(earlier, search_type='raw') & prefix


def _looks_like_a_number(term):
	"""Whether a term is machinery rather than words.

	"Q5:1010" and "x^2-2" are numbers written for a parser; ranking them as
	prose finds nothing and costs a query. This is the dropdown's own test,
	kept so both callers skip the same terms.
	"""
	return ':' in term or '^' in term


def _table_by_number(term):
	"""The table a term names by number, or None.

	Accepts `T12`, `t12` and a bare `12`, because all three are how a table's
	number gets written, and nothing else.

	A draft is not returned. It answers no search by name, and answering one by
	number would be the same disclosure in a different spelling.
	"""
	from .models import Table

	text = (term or '').strip()
	if not text:
		return None
	digits = text[1:] if text[:1] in 'tT' else text
	if not digits.isdigit():
		return None
	return Table.objects.filter(tid_int=int(digits), published=True).first()


def search_metadata(term, limit=METADATA_LIMIT):
	"""Tags and tables whose text matches the term, best first.

	The counterpart to :func:`search_by_term`, which reads a term as a number.
	This reads it as words, against the ``search_vector`` maintained on tags
	and on ``TableSearch``. Both questions are legitimate for the same term,
	and which one the asker meant is not knowable, so both are asked.

	Returns ``(tags, tables)``. Either may be empty; a term that is plainly
	machinery gets neither, without a query being run.
	"""
	from .models import Tag, TableSearch

	term = (term or '').strip()

	#A table's own number, typed straight in. `T12` is how a table is
	#cited, so it is a thing somebody arrives holding -- and it found
	#nothing at all, because a number is not a word and the text index
	#has never held one. Answered directly rather than indexed: it is
	#exact, there is at most one, and an index would only be a slower
	#way to ask.
	numbered = _table_by_number(term)
	if numbered is not None:
		return [], [numbered]

	if not term or _looks_like_a_number(term):
		return [], []

	query = full_text_query(term)
	if query is None:
		return [], []

	rank = SearchRank(F('search_vector'), query)

	def best(manager):
		return list(manager.annotate(rank=rank)
		            .filter(rank__gte=MIN_RANK).order_by('-rank')[:limit])

	tags = best(Tag.objects)
	#Drafts are their author's until published, so they do not answer a search
	#by name any more than they answer one by number.
	tables = [row.table for row in best(
		TableSearch.objects.select_related('table').filter(
			table__published=True))]
	return tags, tables
