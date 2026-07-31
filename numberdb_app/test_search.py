"""What search guarantees, for every kind of number.

These pin down properties that were established by measurement and would
otherwise regress silently, because each failure mode returns *fewer* results
rather than raising:

  - symmetry. A stored value coarser than the query still matches it. This is
    the bug that made a precise query miss the number it was looking for.
  - the score. In (0, 1], and exactly 1 when the stored value lies inside the
    query, which is what licenses the early exit.
  - the early exit. A page of score-1 results ends the search.
  - inclusive range bounds. NumericRange(x, x) defaults to ``[x, x)``, which
    Postgres reads as *empty*; every exactly-known value has lower == upper, so
    getting this wrong deletes all of them from search with no error anywhere.

Run inside the web container, which has Sage:

    docker compose exec -T web sage -python manage.py test numberdb_app.test_search
"""

from django.test import TestCase
from sage.rings.all import CIF, RIF, Qp

from .models import Number, NumberComplex, NumberPAdic, Table
from .search import (_coarser_ball_strings, search_complex_numbers,
                     search_fractional_parts, search_p_adic_numbers,
                     search_real_numbers)


def _table():
	return Table.objects.create(tid='T1', tid_int=1, url='t1', path='t1',
	                            title='Table 1')


class RealSearch(TestCase):

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, param=b'x'):
		number = Number(sage_number=sage_number)
		number.table = self.table
		number.param = param
		number.save()
		return number

	def test_exactly_known_values_are_findable(self):
		"""The [x, x) trap: an empty range would match nothing at all."""
		stored = self.store(RIF(3))
		found = search_real_numbers(RIF(2.5, 3.5), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_coarser_stored_value_matches_a_precise_query(self):
		"""The asymmetry. It cannot sit *inside* the query, but it may be it."""
		stored = self.store(RIF(3.14, 3.15))
		found = search_real_numbers(RIF(3.14159, 3.14160), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_precise_stored_value_matches_a_coarse_query(self):
		stored = self.store(RIF(3.14159, 3.14160))
		found = search_real_numbers(RIF(3.14, 3.15), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_disjoint_values_are_not_returned(self):
		self.store(RIF(9.0, 9.5))
		self.assertEqual(search_real_numbers(RIF(3.0, 4.0), 100), [])

	def test_containment_scores_exactly_one_and_outranks_overlap(self):
		inside = self.store(RIF(3.4, 3.6), param=b'in')
		straddling = self.store(RIF(3.5, 4.5), param=b'out')
		found = search_real_numbers(RIF(3.0, 4.0), 100)

		by_id = {n.id: float(n.overlap_score) for n in found}
		self.assertEqual(by_id[inside.id], 1.0)
		self.assertLess(by_id[straddling.id], 1.0)
		self.assertGreater(by_id[straddling.id], 0.0)
		self.assertEqual(found[0].id, inside.id)

	def test_a_full_page_of_contained_values_ends_the_search(self):
		"""They all score 1, so nothing unexamined can outrank them."""
		for i in range(12):
			self.store(RIF(3 + i / 1000.0), param=bytes([i]))
		self.assertEqual(len(search_real_numbers(RIF(2.0, 4.0), 10)), 10)

	def test_a_saturated_value_stays_findable_and_ranks_last(self):
		"""Beyond what a double holds, so one end of its range is unbounded."""
		huge = self.store(RIF(10) ** 400, param=b'huge')
		self.assertTrue(huge.value_range.upper_inf or huge.value_range.lower_inf)

		near = self.store(RIF(10) ** 400 * RIF(1.000001), param=b'near')
		found = search_real_numbers(RIF(10) ** 400, 100)
		ids = [n.id for n in found]
		self.assertIn(huge.id, ids)
		self.assertIn(near.id, ids)


class ComplexSearch(TestCase):

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, param=b'x'):
		number = NumberComplex(sage_number=sage_number)
		number.table = self.table
		number.param = param
		number.save()
		return number

	def test_a_coarser_stored_value_matches_a_precise_query(self):
		stored = self.store(CIF(RIF(0.4, 0.6), RIF(1.4, 1.6)))
		found = search_complex_numbers(CIF(RIF(0.49, 0.51), RIF(1.49, 1.51)), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_disjoint_boxes_are_not_returned(self):
		self.store(CIF(RIF(5.0, 6.0), RIF(5.0, 6.0)))
		self.assertEqual(
			search_complex_numbers(CIF(RIF(0.0, 1.0), RIF(0.0, 1.0)), 100), [])

	def test_containment_scores_one_and_outranks_partial_overlap(self):
		inside = self.store(CIF(RIF(0.2, 0.4), RIF(0.2, 0.4)), param=b'in')
		half = self.store(CIF(RIF(0.5, 1.5), RIF(0.0, 1.0)), param=b'half')
		found = search_complex_numbers(CIF(RIF(0.0, 1.0), RIF(0.0, 1.0)), 100)

		by_id = {n.id: float(n.overlap_score) for n in found}
		self.assertEqual(by_id[inside.id], 1.0)
		self.assertAlmostEqual(by_id[half.id], 0.5, places=6)

	def test_a_value_exact_in_one_axis_still_scores(self):
		"""A zero-width axis would be 0/0 if the score compared areas."""
		stored = self.store(CIF(RIF(0.5), RIF(-1.0, 3.0)))
		found = search_complex_numbers(CIF(RIF(0.0, 1.0), RIF(0.0, 1.0)), 100)
		by_id = {n.id: float(n.overlap_score) for n in found}
		self.assertAlmostEqual(by_id[stored.id], 0.25, places=6)

	def test_a_full_page_of_contained_boxes_ends_the_search(self):
		#Offset off zero: NumberComplex cannot be constructed at 0, because the
		#Z-order searchstring takes log(10) of the magnitude. See docs/backlog.md.
		for i in range(12):
			self.store(CIF(RIF((i + 1) / 100.0), RIF((i + 1) / 100.0)),
			           param=bytes([i]))
		found = search_complex_numbers(CIF(RIF(-1.0, 1.0), RIF(-1.0, 1.0)), 10)
		self.assertEqual(len(found), 10)


class PAdicSearch(TestCase):

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, param=b'x'):
		number = NumberPAdic(sage_number=sage_number)
		number.table = self.table
		number.param = param
		number.save()
		return number

	def query_string(self, sage_number):
		return NumberPAdic(sage_number=sage_number).number_string

	def test_a_precise_query_finds_a_coarsely_stored_value(self):
		"""The asymmetry, in the direction that used to return nothing."""
		stored = self.store(Qp(5, 20)(1 + 5 + 5 ** 2))
		found = search_p_adic_numbers(
			self.query_string(Qp(5, 40)(1 + 5 + 5 ** 2)), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_coarse_query_finds_a_precisely_stored_value(self):
		stored = self.store(Qp(5, 40)(1 + 5 + 5 ** 2))
		found = search_p_adic_numbers(
			self.query_string(Qp(5, 20)(1 + 5 + 5 ** 2)), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_different_number_is_not_returned(self):
		self.store(Qp(5, 20)(1 + 5 + 5 ** 2))
		found = search_p_adic_numbers(self.query_string(Qp(5, 20)(2 + 5)), 100)
		self.assertEqual(found, [])

	def test_finer_values_rank_above_coarser_ones(self):
		"""Score is p**-(query precision - stored precision), so length orders."""
		coarse = self.store(Qp(5, 10)(1 + 5), param=b'coarse')
		fine = self.store(Qp(5, 30)(1 + 5), param=b'fine')
		found = search_p_adic_numbers(self.query_string(Qp(5, 40)(1 + 5)), 100)

		ids = [n.id for n in found]
		self.assertIn(fine.id, ids)
		self.assertIn(coarse.id, ids)
		self.assertLess(ids.index(fine.id), ids.index(coarse.id))

	def test_prefixes_are_cut_only_at_digit_boundaries(self):
		"""Digits are zero-padded, so for p >= 11 they are multi-character."""
		query = self.query_string(Qp(17, 12)(3 + 5 * 17))
		for candidate in _coarser_ball_strings(query):
			digits = candidate.split(',', 2)[2]
			self.assertTrue(all(len(place) == 2 for place in digits.split('|')),
			                '%s splits a digit' % (candidate,))

	def test_the_query_itself_is_left_to_the_containment_lookup(self):
		query = self.query_string(Qp(5, 20)(1 + 5))
		self.assertNotIn(query, _coarser_ball_strings(query))


class FractionalPartSearch(TestCase):
	"""The last search that still asked for containment."""

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, param=b'x'):
		number = Number(sage_number=sage_number)
		number.table = self.table
		number.param = param
		number.save()
		return number

	def test_a_coarser_stored_fraction_matches_a_precise_query(self):
		"""The bug: it cannot sit inside the query, but it may be it."""
		stored = self.store(RIF(3.14, 3.15))
		found = search_fractional_parts(RIF(0.14159, 0.14160), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_precise_stored_fraction_matches_a_coarse_query(self):
		stored = self.store(RIF(3.14159, 3.14160))
		found = search_fractional_parts(RIF(0.14, 0.15), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_exactly_known_fractions_are_findable(self):
		stored = self.store(RIF(3.5))
		found = search_fractional_parts(RIF(0.4, 0.6), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_negative_number_is_searched_by_its_positive_fraction(self):
		stored = self.store(RIF(-2.3))
		found = search_fractional_parts(RIF(0.69, 0.71), 100)
		self.assertIn(stored.id, [n.id for n in found])

	def test_a_wholly_unknown_fraction_is_not_returned(self):
		"""Straddling an integer, frac() gives [0,1]: no measurement at all.

		It overlaps every query, so admitting it would bury the real matches --
		715 such rows against 5 informative ones for a precise query.
		"""
		unknown = self.store(RIF(3.9, 4.1), param=b'unk')
		known = self.store(RIF(3.7), param=b'known')
		self.assertEqual((float(unknown.frac_range.lower),
		                  float(unknown.frac_range.upper)), (0.0, 1.0))

		ids = [n.id for n in search_fractional_parts(RIF(0.69, 0.71), 100)]
		self.assertIn(known.id, ids)
		self.assertNotIn(unknown.id, ids)

	def test_a_merely_coarse_fraction_is_still_returned(self):
		"""Wide but measured, so unlike [0,1] it is demoted rather than dropped."""
		coarse = self.store(RIF(3.6, 3.8), param=b'coarse')
		ids = [n.id for n in search_fractional_parts(RIF(0.69, 0.71), 100)]
		self.assertIn(coarse.id, ids)

	def test_a_disjoint_fraction_is_not_returned(self):
		self.store(RIF(3.2))
		self.assertEqual(search_fractional_parts(RIF(0.8, 0.9), 100), [])

	def test_a_full_page_of_contained_fractions_ends_the_search(self):
		for i in range(12):
			self.store(RIF(3 + (i + 1) / 1000.0), param=bytes([i]))
		self.assertEqual(len(search_fractional_parts(RIF(0.0, 0.5), 10)), 10)
