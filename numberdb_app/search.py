"""Real-number search: which stored values could be the one being looked for.

Two questions are easy to confuse. The stored value is an exact real that is
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
"""

from django.db.models.expressions import RawSQL

from .models import Number, searchable_range

__all__ = ['search_real_numbers', 'real_query_range']

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
_SCORE_SQL = """
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
		Number.objects.filter(value_range__contained_by = query)[:limit]
	)
	if len(contained) >= limit:
		return contained

	#Fewer than a full page score 1, so the coarser values that merely overlap
	#have to be ranked in. This re-finds the contained ones -- they overlap
	#too -- and sorts the union, so the result is a superset of the above.
	return list(
		Number.objects
			.filter(value_range__overlap = query)
			.annotate(overlap_score = RawSQL(_SCORE_SQL, (query, query)))
			.order_by('-overlap_score')[:limit]
	)
