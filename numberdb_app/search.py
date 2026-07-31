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

from django.db.backends.postgresql.psycopg_any import NumericRange
from django.db.models.expressions import RawSQL

from .models import Number, NumberComplex, NumberPAdic, searchable_range

__all__ = ['search_real_numbers', 'search_fractional_parts',
           'search_complex_numbers', 'search_p_adic_numbers',
           'real_query_range']

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


#Numeric search answers one question: someone has a number from an experiment
#and wants to know whether it is already known. An entry earns a place only if
#matching it says *which* number they have.
#
#A few stored values cannot do that, because nothing better about them is
#known: the exponent of matrix multiplication is somewhere in [2, 2.3728596],
#a diagonal Ramsey number somewhere in [43, 48]. Matching one of those does not
#identify anything -- it reports that a wide range overlaps another wide range,
#and it would do so for every experimental value in that range.
#
#They are recognised without a threshold, because the data already draws this
#line: exact_text renders a value as a decimal expansion when it is known to
#its last digit, and as "[a,b]" when it is not. Eleven of 45832 rows are
#written as intervals, and they are exactly the Ramsey numbers and the matrix
#multiplication exponent.
#
#This removes them from search *by number* only. They remain reachable by name
#and by tag, which is the way to ask about them: "matrix multiplication", not
#"2.3".
def _identifiable(queryset):
	return queryset.exclude(exact_text__startswith = '[')

def real_query_range(r_query):
	"""A Sage real interval as the numrange to search with."""
	return searchable_range(r_query.lower(), r_query.upper())


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

	contained = list(
		_identifiable(Number.objects)
			.filter(value_range__contained_by = query)[:limit]
	)
	if len(contained) >= limit:
		return contained

	#Fewer than a full page score 1, so the coarser values that merely overlap
	#have to be ranked in. This re-finds the contained ones -- they overlap
	#too -- and sorts the union, so the result is a superset of the above.
	return list(
		_identifiable(Number.objects)
			.filter(value_range__overlap = query)
			.annotate(overlap_score = RawSQL(_SCORE_SQL, (query, query)))
			.order_by('-overlap_score')[:limit]
	)


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

	contained = list(
		NumberComplex.objects.filter(
			re_lower__gte = re_low, re_upper__lte = re_high,
			im_lower__gte = im_low, im_upper__lte = im_high,
		)[:limit]
	)
	if len(contained) >= limit:
		return contained

	return list(
		NumberComplex.objects
			.filter(
				re_lower__lte = re_high, re_upper__gte = re_low,
				im_lower__lte = im_high, im_upper__gte = im_low,
			)
			.annotate(overlap_score = RawSQL(
				_COMPLEX_SCORE_SQL, (re_high, re_low, im_high, im_low)))
			.order_by('-overlap_score')[:limit]
	)


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
	inside = list(
		NumberPAdic.objects.filter(
			number_string__startswith = number_string)[:limit]
	)
	if len(inside) >= limit:
		return inside

	coarser = list(
		NumberPAdic.objects.filter(
			number_string__in = _coarser_ball_strings(number_string))
	)
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

	contained = list(
		_identifiable(Number.objects)
			.filter(frac_range__contained_by = query)[:limit]
	)
	if len(contained) >= limit:
		return contained

	return list(
		_identifiable(Number.objects)
			.filter(frac_range__overlap = query)
			.exclude(frac_range__contains = unknown)
			.annotate(overlap_score = RawSQL(_FRAC_SCORE_SQL, (query, query)))
			.order_by('-overlap_score')[:limit]
	)
