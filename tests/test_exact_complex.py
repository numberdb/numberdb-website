"""Tests for utils/numbers/complex.py.

No Sage, no Django, no database:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import (  # noqa: E402
    ExactComplex,
    ParseError,
    parse_complex,
    parse_real,
)


class MixedExactness(unittest.TestCase):
    """The case the four-float schema could not express.

    It stored 5/6 as [0.833333333333333, 0.833333333333334], discarding the
    exactness at import, because there was nowhere to record that one component
    was exact and the other was not.
    """

    def test_exact_real_part_beside_an_uncertain_imaginary_part(self):
        value = parse_complex('5/6 + 5.5I')
        (re_low, re_high), (im_low, im_high) = value.bounds()

        self.assertEqual(re_low, Fraction(5, 6))
        self.assertEqual(re_high, Fraction(5, 6))
        self.assertTrue(value.real().is_exact())

        self.assertEqual(im_low, Fraction(27, 5))      # 5.4
        self.assertEqual(im_high, Fraction(28, 5))     # 5.6
        self.assertFalse(value.imag().is_exact())

    def test_only_the_uncertain_component_is_dotted(self):
        text, dots = parse_complex('5/6 + 5.5I').render()
        self.assertEqual(len(dots), 1)
        self.assertEqual(text[dots[0]], '5')
        #The dot is in the imaginary part, after the joining sign.
        self.assertGreater(dots[0], text.index('+'))

    def test_both_components_uncertain_gives_two_dots(self):
        text, dots = parse_complex('3.14-2.71*I').render()
        self.assertEqual(len(dots), 2)
        self.assertEqual(text[dots[0]], '4')
        self.assertEqual(text[dots[1]], '1')

    def test_exact_components_are_not_dotted(self):
        for source in ['1/2 + 1/3*I', '1*I', '[1/3,1/2]+[0.1,0.2]*I']:
            with self.subTest(source=source):
                _, dots = parse_complex(source).render()
                self.assertEqual(dots, ())


class NegativeImaginaryPart(unittest.TestCase):

    def test_sign_folds_into_the_joiner(self):
        text, _ = parse_complex('3.14-2.71*I').render()
        self.assertIn(' - ', text)
        self.assertNotIn('+ -', text)

    def test_folding_does_not_change_the_value(self):
        #Folding needs exact negation, not string surgery: the bounds must
        #stay the negated originals, in the right order.
        (_, _), (im_low, im_high) = parse_complex('3.14-2.71*I').bounds()
        self.assertEqual(im_low, Fraction(-272, 100))
        self.assertEqual(im_high, Fraction(-270, 100))
        self.assertLess(im_low, im_high)

    def test_interval_component_negates_by_swapping_endpoints(self):
        #`[-0.3, -0.1]` does not begin with a sign that could be moved, so this
        #is the case string surgery would have got wrong.
        value = parse_complex('0 - [0.1,0.3]*I')
        (_, _), (im_low, im_high) = value.bounds()
        self.assertEqual(im_low, Fraction(-3, 10))
        self.assertEqual(im_high, Fraction(-1, 10))


class Grammar(unittest.TestCase):

    def test_documented_forms(self):
        #Front page: "sums or differences of the form A or i*A or A*i".
        expected = parse_complex('-1/2 + i*0.86602').bounds()
        for source in ['-1/2 + 0.86602*i', '-1/2+0.86602i', '-1/2 + i * 0.86602']:
            with self.subTest(source=source):
                self.assertEqual(parse_complex(source).bounds(), expected)

    def test_bare_imaginary_unit(self):
        value = parse_complex('1*I')
        (re_low, re_high), (im_low, im_high) = value.bounds()
        self.assertEqual((re_low, re_high), (0, 0))
        self.assertEqual((im_low, im_high), (1, 1))
        self.assertEqual(parse_complex('i').bounds(), value.bounds())

    def test_interval_components_in_both_positions(self):
        value = parse_complex('[1/3,1/2]+[0.1,0.2]*I')
        (re_low, re_high), (im_low, im_high) = value.bounds()
        self.assertEqual((re_low, re_high), (Fraction(1, 3), Fraction(1, 2)))
        self.assertEqual((im_low, im_high), (Fraction(1, 10), Fraction(1, 5)))

    def test_exponents_are_not_split_as_signs(self):
        value = parse_complex('1e-5+2e-5*I')
        (re_low, re_high), _ = value.bounds()
        self.assertLess(re_low, Fraction(1, 100000))
        self.assertGreater(re_high, Fraction(1, 100000))

    def test_several_terms_on_one_axis_are_refused(self):
        #Summing them needs arithmetic on notations -- the sum of two decimal
        #expansions is not an expansion -- and the grammar does not ask for it.
        for source in ['1/2 + 1/3 + 2*I', '1*I + 2*I']:
            with self.subTest(source=source):
                with self.assertRaises(ParseError):
                    parse_complex(source)

    def test_rejects_undocumented_text(self):
        for source in ['', 'hello', '1 + ?*I']:
            with self.subTest(source=source):
                with self.assertRaises(ParseError):
                    parse_complex(source)


class RoundTripAndValueSemantics(unittest.TestCase):

    SAMPLES = ['5/6 + 5.5I', '-1/2 + i*0.86602', '3.14-2.71*I', '1*I',
               '[1/3,1/2]+[0.1,0.2]*I', '0.001+1e-5*I']

    def test_render_parse_render_is_stationary(self):
        for source in self.SAMPLES:
            with self.subTest(source=source):
                once, _ = parse_complex(source).render()
                twice, _ = parse_complex(once).render()
                self.assertEqual(once, twice)

    def test_bounds_survive_the_round_trip_exactly(self):
        for source in self.SAMPLES:
            with self.subTest(source=source):
                original = parse_complex(source)
                rendered, _ = original.render()
                self.assertEqual(parse_complex(rendered).bounds(),
                                 original.bounds())

    def test_equality_is_by_value(self):
        self.assertEqual(parse_complex('5/6+5.5*I'), parse_complex('5/6 + 5.5I'))
        self.assertEqual(hash(parse_complex('5/6+5.5*I')),
                         hash(parse_complex('5/6 + 5.5I')))
        self.assertNotEqual(parse_complex('5/6+5.5*I'),
                            parse_complex('5/6+5.50*I'))


class SearchBox(unittest.TestCase):

    def test_box_contains_the_exact_bounds(self):
        for source in ['5/6 + 5.5I', '-1/2 + i*0.86602', '1/3+1/7*I']:
            with self.subTest(source=source):
                value = parse_complex(source)
                (re_low, re_high), (im_low, im_high) = value.bounds()
                box_re_low, box_re_high, box_im_low, box_im_high = value.search_box()
                self.assertLessEqual(Fraction(box_re_low), re_low)
                self.assertGreaterEqual(Fraction(box_re_high), re_high)
                self.assertLessEqual(Fraction(box_im_low), im_low)
                self.assertGreaterEqual(Fraction(box_im_high), im_high)

    def test_overlap_is_symmetric_unlike_prefix_matching(self):
        #The property the Z-order index lacked: a coarse value and a precise
        #one inside it must find each other in both directions.
        coarse = parse_complex('[0.4,0.6]+[0.2,0.3]*I')
        precise = parse_complex('0.5+0.25*I')
        self.assertTrue(coarse.overlaps(precise))
        self.assertTrue(precise.overlaps(coarse))
        self.assertTrue(coarse.contains(precise))
        self.assertFalse(precise.contains(coarse))

    def test_disjoint_boxes_do_not_overlap(self):
        self.assertFalse(parse_complex('0.5+0.25*I')
                         .overlaps(parse_complex('9+9*I')))

    def test_components_must_be_exact_reals(self):
        with self.assertRaises(TypeError):
            ExactComplex(parse_real('1'), 2)


if __name__ == '__main__':
    unittest.main()
