"""Tests for utils/numbers/real.py.

No Sage, no Django, no database:

    python3 -m unittest discover -s tests -v

The specification is the two user-facing documents -- help.html section "Number
types and displayed accuracy", and the front-page tips in
templates/includes/search-tips.html -- so their worked examples are the tests.
"""

import math
import os
import sys
import unittest
from decimal import Decimal
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import ExactReal, ParseError, parse_real  # noqa: E402


class DocumentedFormats(unittest.TestCase):
    """Every format, with the bounds the documentation states."""

    CASES = [
        # (text, lower, upper)
        ('42',             Fraction(42), Fraction(42)),
        ('-1729',          Fraction(-1729), Fraction(-1729)),
        ('-3/2',           Fraction(-3, 2), Fraction(-3, 2)),
        ('5/6',            Fraction(5, 6), Fraction(5, 6)),
        ('3.14',           Fraction(313, 100), Fraction(315, 100)),
        ('12e2',           Fraction(1100), Fraction(1300)),
        ('1p31415',        Fraction(31414, 10000), Fraction(31416, 10000)),
        ('[2, 2.3728596]', Fraction(2), Fraction(23728596, 10000000)),
        ('3.14 +/- 2e-2',  Fraction(312, 100), Fraction(316, 100)),
    ]

    def test_bounds_match_the_documentation(self):
        for text, low, high in self.CASES:
            with self.subTest(text=text):
                lower, upper = parse_real(text).bounds()
                self.assertEqual(lower, low, '%r lower bound' % (text,))
                self.assertEqual(upper, high, '%r upper bound' % (text,))

    def test_bounds_are_exact_not_approximate(self):
        #The whole point of the redesign: no binary rounding anywhere.
        lower, upper = parse_real('3.14').bounds()
        self.assertIsInstance(lower, Fraction)
        self.assertEqual(lower, Fraction(313, 100))

        #3.13 has no exact binary representation, so the double differs from
        #the true value. Storing that double is what used to lose precision;
        #the Fraction does not.
        as_stored_before = Fraction(3.13)          # exact value of the double
        self.assertNotEqual(as_stored_before, Fraction(313, 100))
        self.assertEqual(lower, Fraction(313, 100))

    def test_value_without_point_or_exponent_is_exact(self):
        #Documented: "If the decimal expansion does not contain '.' or 'e', it
        #will instead denote an exactly represented integer."
        self.assertTrue(parse_real('42').is_exact())
        self.assertFalse(parse_real('42e0').is_exact())
        self.assertFalse(parse_real('4.2').is_exact())

    def test_rationals_with_arbitrary_denominators(self):
        #Bernoulli numbers are exact rationals that are not 10-smooth, which is
        #why the notation layer cannot be Decimal alone.
        for text, expected in [('1/6', Fraction(1, 6)),
                               ('-1/30', Fraction(-1, 30)),
                               ('-691/2730', Fraction(-691, 2730))]:
            with self.subTest(text=text):
                value = parse_real(text)
                self.assertTrue(value.is_exact())
                self.assertEqual(value.bounds()[0], expected)

    def test_interval_endpoints_may_be_rational(self):
        #Previously unparseable in every format -- a gap, not a decision.
        lower, upper = parse_real('[1/3, 1/2]').bounds()
        self.assertEqual(lower, Fraction(1, 3))
        self.assertEqual(upper, Fraction(1, 2))

    def test_rejects_undocumented_text(self):
        for text in ['', 'hello', '3.14?', '1/0/2', '[1]', '[1,2,3]']:
            with self.subTest(text=text):
                with self.assertRaises(ParseError):
                    parse_real(text)


class SignificanceIsPreserved(unittest.TestCase):
    """Trailing zeros are load-bearing; Fraction alone would discard them."""

    def test_trailing_zeros_narrow_the_interval(self):
        widths = [parse_real(t).width() for t in ['3.14', '3.140', '3.1400']]
        self.assertEqual(widths[0], Fraction(2, 100))
        self.assertEqual(widths[1], Fraction(2, 1000))
        self.assertEqual(widths[2], Fraction(2, 10000))
        self.assertGreater(widths[0], widths[1])
        self.assertGreater(widths[1], widths[2])

    def test_same_rational_different_intervals(self):
        #Both are 157/50 as rationals. They are not the same number here.
        self.assertEqual(Fraction(Decimal('3.14')), Fraction(Decimal('3.1400')))
        self.assertNotEqual(parse_real('3.14'), parse_real('3.1400'))

    def test_scientific_notation_does_not_gain_precision(self):
        #12e2 means [1100, 1300]. Rendering it as "1200" would mean
        #[1199, 1201] -- a hundredfold false gain in precision.
        rendered, _ = parse_real('12e2').render()
        self.assertNotEqual(rendered, '1200')
        self.assertEqual(parse_real(rendered).bounds(), parse_real('12e2').bounds())


class RoundTripIsAFixedPoint(unittest.TestCase):
    """The property float storage could never have.

    With binary storage the cycle degraded a digit per pass
    (3.14159 -> 3.1416 -> 3.142). Exact bounds make it stationary.
    """

    SAMPLES = ['42', '-1729', '-3/2', '5/6', '1/6', '3.14', '3.1400', '12e2',
               '0.001', '-1.5e-3', '1p31415', '[2, 2.3728596]', '[1/3, 1/2]',
               '3.14 +/- 2e-2', '1.2345678901234567890123456789']

    def test_render_parse_render_is_stationary(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                once, _ = parse_real(text).render()
                twice, _ = parse_real(once).render()
                self.assertEqual(once, twice, 'rendering is not stationary')

    def test_bounds_survive_the_round_trip_exactly(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                original = parse_real(text)
                rendered, _ = original.render()
                self.assertEqual(parse_real(rendered).bounds(), original.bounds())

    def test_a_hundred_digit_value_is_not_degraded(self):
        text = '3.' + '1415926535' * 10          # 100 fractional digits
        original = parse_real(text)
        rendered, _ = original.render()
        self.assertEqual(rendered, text)
        self.assertEqual(parse_real(rendered).bounds(), original.bounds())


class DottedDigit(unittest.TestCase):
    """The index is present exactly for expansions, so no dot means exact."""

    def test_expansions_mark_their_last_mantissa_digit(self):
        for text, expected_digit in [('3.14', '4'), ('12e2', '2'),
                                     ('0.001', '1'), ('-1.5e-3', '5')]:
            with self.subTest(text=text):
                rendered, index = parse_real(text).render()
                self.assertIsNotNone(index, '%r should mark a digit' % (text,))
                self.assertEqual(rendered[index], expected_digit)

    def test_the_marked_digit_is_in_the_mantissa_not_the_exponent(self):
        rendered, index = parse_real('12e2').render()
        self.assertLess(index, rendered.index('e'))

    def test_exact_values_mark_nothing(self):
        for text in ['42', '-3/2', '5/6', '[2, 2.3728596]', '3.14 +/- 2e-2']:
            with self.subTest(text=text):
                _, index = parse_real(text).render()
                self.assertIsNone(index, '%r must not mark a digit' % (text,))


class SearchBoundsAreSound(unittest.TestCase):
    """The index may over-approximate; it must never under-approximate."""

    def test_float_bounds_contain_the_exact_bounds(self):
        for text in ['3.14', '5/6', '1/6', '12e2', '[2, 2.3728596]',
                     '3.14 +/- 2e-2', '0.001', '-1.5e-3', '1/3']:
            with self.subTest(text=text):
                value = parse_real(text)
                low, high = value.bounds()
                float_low, float_high = value.search_bounds()
                self.assertLessEqual(Fraction(float_low), low,
                                     'lower search bound is too high')
                self.assertGreaterEqual(Fraction(float_high), high,
                                        'upper search bound is too low')

    def test_huge_magnitudes_do_not_raise(self):
        #float(10**400) raises OverflowError; 310 production rows already
        #saturate float64.
        value = parse_real('1' + '0' * 400)
        low, high = value.search_bounds()
        self.assertTrue(math.isinf(high) or high == sys.float_info.max)
        self.assertLessEqual(Fraction(low), value.bounds()[0])

    def test_thousand_digit_integer_is_exact(self):
        text = '9' * 1000
        value = parse_real(text)
        self.assertTrue(value.is_exact())
        self.assertEqual(value.bounds()[0], Fraction(int(text)))


class ValueSemantics(unittest.TestCase):

    def test_equality_is_by_value_not_spelling(self):
        self.assertEqual(parse_real('3.14'), parse_real('[3.13, 3.15]'))
        self.assertEqual(hash(parse_real('3.14')), hash(parse_real('[3.13, 3.15]')))

    def test_p_notation_normalises_to_an_expansion(self):
        #Its own documentation defines it by translation, so it is not kept as
        #a notation of its own.
        self.assertEqual(parse_real('1p31415'), parse_real('3.1415'))
        rendered, index = parse_real('1p31415').render()
        self.assertEqual(rendered, '3.1415')
        self.assertIsNotNone(index)

    def test_overlap_and_containment(self):
        loose = parse_real('3.14')            # [3.13, 3.15]
        tight = parse_real('3.14159')         # inside it
        far = parse_real('99')
        self.assertTrue(loose.overlaps(tight))
        self.assertTrue(loose.contains(tight))
        self.assertFalse(tight.contains(loose))
        self.assertFalse(loose.overlaps(far))

    def test_exact_values_have_zero_width(self):
        self.assertEqual(parse_real('5/6').width(), 0)
        self.assertGreater(parse_real('3.14').width(), 0)


if __name__ == '__main__':
    unittest.main()
