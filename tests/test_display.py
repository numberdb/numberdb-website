"""Tests for utils/numbers/display.py -- the uniform search-result view.

No Sage:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import parse_real  # noqa: E402
from utils.numbers.display import uniform_real_text  # noqa: E402


class Soundness(unittest.TestCase):
    """The displayed value must never claim more than is known.

    This is the property that matters; the exact spelling is presentation.
    """

    INTERVALS = [
        (Fraction(3), Fraction(3)),
        (Fraction(-1, 2), Fraction(-1, 2)),
        (Fraction(313, 100), Fraction(315, 100)),
        (Fraction(54, 10), Fraction(56, 10)),
        (Fraction(1100), Fraction(1300)),
        (Fraction(-1, 10), Fraction(1, 10)),
        (Fraction(0), Fraction(0)),
        (Fraction(10) ** 21, Fraction(10000001) * Fraction(10) ** 14),
        (Fraction(2), Fraction(23728596, 10 ** 7)),
        (Fraction(31415926, 10 ** 7), Fraction(31415928, 10 ** 7)),
        (Fraction(-27, 5), Fraction(-26, 5)),
        (Fraction(1, 3), Fraction(1, 2)),
    ]

    def test_displayed_value_reparses_and_contains_the_original(self):
        for low, high in self.INTERVALS:
            with self.subTest(interval=(low, high)):
                text = uniform_real_text(low, high)
                shown = parse_real(text)
                shown_low, shown_high = shown.bounds()
                self.assertLessEqual(shown_low, low,
                                     '%s excludes part of the value' % (text,))
                self.assertGreaterEqual(shown_high, high,
                                        '%s excludes part of the value' % (text,))

    def test_never_renders_a_question_mark(self):
        for low, high in self.INTERVALS:
            with self.subTest(interval=(low, high)):
                self.assertNotIn('?', uniform_real_text(low, high))


class ExactValues(unittest.TestCase):
    """Rendered exactly, because a period would claim they are intervals."""

    def test_integers(self):
        self.assertEqual(uniform_real_text(Fraction(3), Fraction(3)), '3')
        self.assertEqual(uniform_real_text(Fraction(0), Fraction(0)), '0')
        self.assertEqual(uniform_real_text(Fraction(-1729), Fraction(-1729)), '-1729')

    def test_rationals(self):
        #The Sage path produced "-0.50000000000000000" here, which under the
        #documented convention asserts an interval known to seventeen places.
        self.assertEqual(uniform_real_text(Fraction(-1, 2), Fraction(-1, 2)), '-1/2')
        self.assertEqual(uniform_real_text(Fraction(1, 6), Fraction(1, 6)), '1/6')

    def test_exact_values_have_no_period(self):
        for value in [Fraction(3), Fraction(-1729), Fraction(0)]:
            with self.subTest(value=value):
                self.assertNotIn('.', uniform_real_text(value, value))


class ChoiceOfForm(unittest.TestCase):

    def test_tight_intervals_become_a_decimal_expansion(self):
        text = uniform_real_text(Fraction(31415926, 10 ** 7),
                                 Fraction(31415928, 10 ** 7))
        self.assertEqual(text, '3.1415927')

    def test_wide_intervals_become_brackets(self):
        text = uniform_real_text(Fraction(2), Fraction(23728596, 10 ** 7))
        self.assertTrue(text.startswith('[') and text.endswith(']'))

    def test_intervals_containing_zero_become_brackets(self):
        #Relative precision is meaningless across zero.
        text = uniform_real_text(Fraction(-1, 10), Fraction(1, 10))
        self.assertTrue(text.startswith('['))

    def test_the_tightest_containing_place_is_chosen(self):
        #10**e >= 2*radius always suffices but assumes the worst case for
        #rounding; a finer place usually works and says more.
        text = uniform_real_text(Fraction(31415926535, 10 ** 10),
                                 Fraction(31415926537, 10 ** 10))
        self.assertEqual(text, '3.1415926536')

    def test_large_magnitudes_use_normalised_scientific_form(self):
        text = uniform_real_text(Fraction(10) ** 21,
                                 Fraction(10000001) * Fraction(10) ** 14)
        self.assertIn('e21', text)
        self.assertNotIn('e14', text)

    def test_bracket_endpoints_are_exact_and_so_unmarked(self):
        #Interval endpoints are exact by definition, so they carry no period
        #purely to signal uncertainty.
        text = uniform_real_text(Fraction(1100), Fraction(1300))
        self.assertEqual(text, '[1100,1300]')


if __name__ == '__main__':
    unittest.main()
