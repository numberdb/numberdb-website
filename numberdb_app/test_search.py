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

from .models import (Number, NumberComplex, NumberPAdic, Polynomial,
                     Table)
from .search import (_coarser_ball_strings, full_text_query, search_by_term,
                     search_metadata,
                     search_complex_numbers, search_fractional_parts,
                     search_p_adic_numbers, search_real_numbers)


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


class IdentifiabilityByNumber(TestCase):
	"""Numeric search answers "is my experimental number known?".

	A value that is only bounded -- the exponent of matrix multiplication, a
	diagonal Ramsey number -- cannot answer it: matching one says a wide range
	overlaps another, for every value in that range. Such entries stay
	reachable by name and tag, which is how to ask about them.
	"""

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, exact_text, param=b'x'):
		from .models import exact_relative_width
		number = Number(sage_number=sage_number)
		number.table = self.table
		number.param = param
		number.exact_text = exact_text
		number.exact_relative_width = exact_relative_width(exact_text)
		number.save()
		return number

	def test_a_merely_bounded_value_is_not_a_numeric_search_result(self):
		#The exponent of matrix multiplication, as actually stored.
		omega = self.store(RIF(2, 2.3728596), '[2, 2.3728596]')
		found = search_real_numbers(RIF(2.2, 2.3), 100)
		self.assertNotIn(omega.id, [n.id for n in found])

	def test_a_measured_value_is_judged_on_what_is_known_not_its_projection(self):
		"""101471818419863/165 projects to a span of 1.2e-4 but is exact."""
		wide = self.store(RIF(2, 2.3728596), '2.20000000000000000')
		found = search_real_numbers(RIF(2.2, 2.3), 100)
		self.assertIn(wide.id, [n.id for n in found])

	def test_a_weakly_measured_value_is_excluded(self):
		"""0.88153(17): a real constant, but not to five significant digits."""
		ratio = self.store(RIF(0.88136, 0.88170), '0.88153(17)')
		found = search_real_numbers(RIF(0.8815, 0.8816), 100)
		self.assertNotIn(ratio.id, [n.id for n in found])

	def test_an_unparsable_value_is_kept(self):
		"""A null width is missing information, not a reason to hide a row."""
		odd = self.store(RIF(2.2, 2.3), '')
		self.assertIsNone(odd.exact_relative_width)
		found = search_real_numbers(RIF(2.2, 2.3), 100)
		self.assertIn(odd.id, [n.id for n in found])

	def test_bounded_values_are_excluded_from_fractional_part_search_too(self):
		ramsey = self.store(RIF(43, 48), '[43, 48]')
		found = search_fractional_parts(RIF(0.4, 0.6), 100)
		self.assertNotIn(ramsey.id, [n.id for n in found])


class ThresholdIsConfigurable(TestCase):
	"""The cutoff is a setting, and the tables must agree with it.

	Search reads a stored measurement and the tables re-derive it from the
	text, so the two could drift apart and tell a reader that a number is
	findable when it is not.
	"""

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, sage_number, exact_text):
		from .models import exact_relative_width
		number = Number(sage_number=sage_number)
		number.table = self.table
		number.param = b'x'
		number.exact_text = exact_text
		number.exact_relative_width = exact_relative_width(exact_text)
		number.save()
		return number

	def test_a_looser_setting_admits_the_mass_ratios(self):
		from django.test import override_settings
		ratio = self.store(RIF(0.88136, 0.88170), '0.88153(17)')
		with override_settings(NUMBERDB_MAX_RELATIVE_WIDTH=1e-3):
			found = search_real_numbers(RIF(0.8815, 0.8816), 100)
			self.assertIn(ratio.id, [n.id for n in found])
		with override_settings(NUMBERDB_MAX_RELATIVE_WIDTH=1e-5):
			found = search_real_numbers(RIF(0.8815, 0.8816), 100)
			self.assertNotIn(ratio.id, [n.id for n in found])

	def test_the_table_mark_tracks_the_same_setting(self):
		from django.test import override_settings
		from .models import findable_by_number
		with override_settings(NUMBERDB_MAX_RELATIVE_WIDTH=1e-3):
			self.assertTrue(findable_by_number('0.88153(17)'))
			self.assertFalse(findable_by_number('[2, 2.3728596]'))
		with override_settings(NUMBERDB_MAX_RELATIVE_WIDTH=1e-5):
			self.assertFalse(findable_by_number('0.88153(17)'))


class SearchPanel(TestCase):
	"""Enter and the magnifier submit a search that has its own URL."""

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()
		from .models import exact_relative_width
		number = Number(sage_number=RIF(3.14159265358979))
		number.table = cls.table
		number.param = b'pi'
		number.exact_text = '3.14159265358979323846'
		number.exact_relative_width = exact_relative_width(number.exact_text)
		number.save()
		cls.pi = number

	def test_the_front_page_still_works_without_a_query(self):
		response = self.client.get('/')
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'id="search-results"')

	def test_a_query_in_the_url_returns_results(self):
		"""The point of the form: a search is a URL that can be shared."""
		response = self.client.get('/', {'q': '3.14159265358979'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id="search-results"')
		self.assertContains(response, 'Real numbers')

	def test_the_term_is_put_back_in_the_box(self):
		response = self.client.get('/', {'q': '3.14159265358979'})
		self.assertContains(response, 'value="3.14159265358979"')

	def test_a_term_matching_nothing_says_so_and_explains(self):
		response = self.client.get('/', {'q': 'zzzznotanumber'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'No match for')
		self.assertContains(response, '#search-precision')

	def test_whitespace_only_is_not_a_search(self):
		response = self.client.get('/', {'q': '   '})
		self.assertNotContains(response, 'id="search-results"')

	def test_the_form_submits_to_the_home_page_by_get(self):
		response = self.client.get('/')
		self.assertContains(response, 'id="searchbox-form"')
		self.assertContains(response, 'method="get"')
		self.assertContains(response, 'name="q"')

	def test_results_are_grouped_by_how_the_term_was_read(self):
		groups = search_by_term('3.14159265358979')
		self.assertEqual([g['kind'] for g in groups], ['real'])

	def test_an_unparsable_term_yields_no_groups_rather_than_raising(self):
		self.assertEqual(search_by_term('zzzznotanumber'), [])
		self.assertEqual(search_by_term(''), [])
		self.assertEqual(search_by_term(None), [])


class TemplatesRenderCleanly(TestCase):
	"""No template syntax may reach the page.

	{# #} is a single-line comment in Django. Spanning lines with it does not
	comment anything out -- the text is rendered, and a four-line note about
	why the search form uses GET appeared on the front page. Nothing failed:
	the page returned 200 with the explanation printed above the search box.
	"""

	MARKERS = ['{#', '#}', '{% comment', '{% endcomment']

	def assert_clean(self, url, data=None):
		page = self.client.get(url, data or {}).content.decode('utf8', 'replace')
		for marker in self.MARKERS:
			self.assertNotIn(marker, page,
			                 '%s leaked %r into the page' % (url, marker))

	def test_the_front_page_is_clean(self):
		self.assert_clean('/')

	def test_the_results_panel_is_clean(self):
		self.assert_clean('/', {'q': '3.14159265358979'})

	def test_the_empty_results_panel_is_clean(self):
		self.assert_clean('/', {'q': 'zzzznotanumber'})

	def test_the_help_page_is_clean(self):
		self.assert_clean('/help')


class InPlaceUpdate(TestCase):
	"""The panel updates without rebuilding the page, and the URL follows.

	The full response stays the definition of what a search URL means: it is
	what a shared link renders, what a search engine sees, and what happens if
	the script never runs. The fragment only spares the page a reload.
	"""

	AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()
		from .models import exact_relative_width
		number = Number(sage_number=RIF(3.14159265358979))
		number.table = cls.table
		number.param = b'pi'
		number.exact_text = '3.14159265358979323846'
		number.exact_relative_width = exact_relative_width(number.exact_text)
		number.save()

	def test_the_fragment_is_only_the_panel(self):
		response = self.client.get('/', {'q': '3.14159265358979'}, **self.AJAX)
		page = response.content.decode()
		self.assertIn('id="search-results"', page)
		for chrome in ['<html', '<head', 'navbar', 'searchbox-form']:
			self.assertNotIn(chrome, page,
			                 'fragment should not carry %r' % (chrome,))

	def test_the_fragment_and_the_full_page_agree(self):
		"""The two must not drift: one is what a visitor sees, the other what
		a shared link renders."""
		import re
		full = self.client.get('/', {'q': '3.14159265358979'}).content.decode()
		fragment = self.client.get('/', {'q': '3.14159265358979'},
		                           **self.AJAX).content.decode()
		panel = re.search(r'<div id="search-results".*</div>', full, re.S)
		self.assertIsNotNone(panel)
		summary = lambda page: ' '.join(
			re.search(r'search-results-summary">(.*?)</div>',
			          page, re.S).group(1).split())
		self.assertEqual(summary(full), summary(fragment))
		self.assertIn('1 result', summary(fragment))

	def test_an_empty_term_clears_the_panel(self):
		response = self.client.get('/', {'q': ''}, **self.AJAX)
		self.assertEqual(response.content.decode().strip(), '')

	def test_the_full_page_still_renders_the_panel_without_the_script(self):
		"""What a shared link must show."""
		response = self.client.get('/', {'q': '3.14159265358979'})
		self.assertContains(response, 'id="search-results"')
		self.assertContains(response, 'search-results-container')

	def test_the_container_is_present_even_with_no_search(self):
		"""It must exist to be replaced, and its absence means 'no panel here'."""
		self.assertContains(self.client.get('/'), 'search-results-container')


class SearchTipsToggle(TestCase):
	"""The tips close when a search is submitted, and the link is addressable.

	The toggle was passed 'searchbar-help', which is a class and matches no
	element. getElementById returned null and the label assignment threw, after
	the panel had already been shown or hidden -- so the tips toggled and the
	link never changed its text.
	"""

	def test_the_toggle_link_has_the_id_it_is_passed(self):
		page = self.client.get('/').content.decode()
		self.assertIn('id="searchtips-toggle"', page)
		self.assertIn("toggle_visibility('searchtips','searchtips-toggle')", page)

	def test_the_old_class_name_is_no_longer_used_as_an_id(self):
		page = self.client.get('/').content.decode()
		self.assertNotIn("toggle_visibility('searchtips','searchbar-help')", page)

	def test_submitting_closes_the_tips(self):
		page = self.client.get('/').content.decode()
		self.assertIn('close_searchtips', page)
		submit = page.index("form.on('submit'")
		self.assertIn('close_searchtips()', page[submit:submit + 400])


class SearchByValue(TestCase):
	"""Searching for a number the caller already has.

	The cheap path: a parse and an indexed query, where the expression endpoint
	forks a sandboxed Sage process to compute a number the caller was holding
	all along.
	"""

	@classmethod
	def setUpTestData(cls):
		cls.table = _table()

	def store(self, model, value, exact_text='', param=b'x'):
		from .models import exact_relative_width
		if model is Polynomial:
			obj = model(sage_polynomial=value)
		else:
			obj = model(sage_number=value)
		obj.table = self.table
		obj.param = param
		obj.exact_text = exact_text
		if hasattr(obj, 'exact_relative_width'):
			obj.exact_relative_width = exact_relative_width(exact_text)
		obj.save()
		return obj

	def test_each_kind_of_value_is_dispatched_on_its_parent(self):
		"""Not on its attributes: Sage polynomials and p-adics both expose
		numerator() and denominator(), so sniffing for those would take them
		for rationals."""
		from sage.rings.all import CIF, QQ, RIF, ZZ, Qp
		from .search import search_number
		ring = QQ['x']
		cases = [
			#'13/4', not '3.25': a decimal expansion claims an uncertain last
			#digit, which is too weak to be searchable by number at all.
			(Number, RIF(3.25), '13/4', RIF(3.25)),
			(Number, ZZ(7), '7', ZZ(7)),
			(Number, QQ(2) / 3, '2/3', QQ(2) / 3),
			(NumberComplex, CIF(RIF(0.5), RIF(1.5)), '0.5 + 1.5*I',
			 CIF(RIF(0.5), RIF(1.5))),
			(NumberPAdic, Qp(5, 20)(1 + 5), '1 + O(5^20)', Qp(5, 20)(1 + 5)),
			(Polynomial, ring([-1, 1]), 'x - 1', ring([-1, 1])),
		]
		for index, (model, stored, text, query) in enumerate(cases):
			with self.subTest(model=model.__name__):
				kept = self.store(model, stored, text, param=bytes([index]))
				found = search_number(query)
				self.assertIn(kept.id, [n.id for n in found],
				              '%s not found by value' % (model.__name__,))

	def test_an_unsupported_parent_is_refused_by_name(self):
		from sage.all import SR
		from .search import search_number
		with self.assertRaises(ValueError):
			search_number(SR('x + 1'))


class CanonicalisationsAgree(TestCase):
	"""The pure-Python polynomial key must partition exactly as the Sage one.

	Two canonicalisations exist because a migration was left half-finished:
	polynomial_modulo_variable_names, in Sage, builds the stored key, while
	canonical_under_renaming, in plain Python, was written to replace it and
	never adopted -- the formats differ, so swapping means rebuilding the key
	for every stored polynomial.

	What matters is not that the keys look alike, which they do not, but that
	they group the same polynomials together. If they do, the stored key can be
	replaced without changing which polynomials find each other, and the plain
	Python one can be shipped to clients so a lookup need send only a hash.
	"""

	def test_the_same_polynomials_are_identified(self):
		from collections import defaultdict
		from utils.numbers.polynomial import parse_polynomial

		by_sage, by_python, unparsed = defaultdict(set), defaultdict(set), 0
		for row in Polynomial.objects.all().iterator(chunk_size=300):
			try:
				key = parse_polynomial(row.exact_text).canonical_text()
			except Exception:
				unparsed += 1
				continue
			by_sage[row.number_string].add(row.pk)
			by_python[key].add(row.pk)

		if not by_sage:
			self.skipTest('no polynomials in this database')
		self.assertEqual(unparsed, 0, 'the Python parser must read them all')
		self.assertEqual({frozenset(v) for v in by_sage.values()},
		                 {frozenset(v) for v in by_python.values()},
		                 'the two canonicalisations group differently')

	def test_renaming_does_not_change_the_key(self):
		from utils.numbers.polynomial import parse_polynomial
		for one, other in [('x^2-2', 'y^2-2'), ('x^2*y', 'y^2*x'),
		                   ('x', 'y'), ('2', '2/1')]:
			with self.subTest(pair=(one, other)):
				self.assertEqual(parse_polynomial(one).canonical_text(),
				                 parse_polynomial(other).canonical_text())

	def test_different_polynomials_keep_different_keys(self):
		from utils.numbers.polynomial import parse_polynomial
		self.assertNotEqual(parse_polynomial('x^2+1').canonical_text(),
		                    parse_polynomial('x^3+1').canonical_text())

	def test_the_hash_is_wide_enough_to_stand_alone(self):
		"""A hash-only lookup cannot be cross-checked against the full text."""
		from utils.numbers.polynomial import parse_polynomial
		digest = parse_polynomial('x^2-2').canonical_hash()
		self.assertEqual(len(digest), 32)          # 128 bits, hex


class MetadataSearch(TestCase):
	"""Words, as opposed to digits.

	The dropdown has always searched table titles and tags; the submitted
	search and the API did not, because the query lived inside the dropdown's
	view. Typing "matrix multiplication" offered the table, and pressing Enter
	then found nothing -- results vanished by committing to the search. These
	pin the shared implementation both now use.
	"""

	def test_a_term_of_machinery_is_not_offered_to_the_word_search(self):
		"""No query is run for something plainly written for a parser."""
		self.assertEqual(search_metadata('Q5:1010'), ([], []))
		self.assertEqual(search_metadata('x^2-2'), ([], []))

	def test_an_empty_term_asks_nothing(self):
		self.assertEqual(search_metadata(''), ([], []))
		self.assertEqual(search_metadata('   '), ([], []))
		self.assertEqual(search_metadata(None), ([], []))

	def test_the_last_word_is_a_prefix_so_typing_finds_things_early(self):
		"""'multiplicat' must already match 'multiplication'."""
		self.assertIsNotNone(full_text_query('multiplicat'))
		self.assertIsNotNone(full_text_query('matrix multiplication'))

	def test_a_term_of_only_spaces_has_no_query(self):
		self.assertIsNone(full_text_query('   '))
		self.assertIsNone(full_text_query(''))

	def test_a_quote_in_a_term_cannot_be_read_as_query_syntax(self):
		"""The old spelling interpolated words bare into raw tsquery."""
		query = full_text_query("d'Alembert constant")
		self.assertIsNotNone(query)

	def test_metadata_search_runs_against_the_database(self):
		"""Empty test database, so this checks the query executes, not hits."""
		tags, tables = search_metadata('matrix multiplication')
		self.assertEqual((list(tags), list(tables)), ([], []))
