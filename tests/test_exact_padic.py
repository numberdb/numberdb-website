"""Tests for utils/numbers/padic.py.

No Sage, no Django, no database:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import ExactPAdic, ParseError, parse_p_adic  # noqa: E402


class DocumentedFormats(unittest.TestCase):
    """The worked examples from help.html and the front-page tips."""

    def test_rational_representative(self):
        value = parse_p_adic('3 + O(2^5)')
        self.assertEqual(value.prime(), 2)
        self.assertEqual(value.precision(), 5)
        self.assertEqual(value.representative(), 3)

    def test_expression_representative(self):
        #Documented as "an algebraic expression involving integers and the
        #usual operations".
        self.assertEqual(parse_p_adic('2^0+2^1+O(2^5)'), parse_p_adic('3 + O(2^5)'))

    def test_rational_with_p_in_the_denominator(self):
        value = parse_p_adic('3/5 + O(5^1)')
        self.assertEqual(value.prime(), 5)
        self.assertEqual(value.precision(), 1)
        self.assertEqual(value.valuation(), -1)
        self.assertEqual(value.representative(), Fraction(3, 5))

    def test_zero_to_a_stated_precision(self):
        value = parse_p_adic('O(2^167)')
        self.assertEqual(value.representative(), 0)
        self.assertEqual(value.precision(), 167)
        self.assertEqual(value.render()[0], 'O(2^167)')

    def test_digit_notation(self):
        #help.html: Q2:1010 is 2^0 + 2^2 + O(2^4); precision is the number of
        #digits after the point.
        value = parse_p_adic('Q2:1010')
        self.assertEqual(value.prime(), 2)
        self.assertEqual(value.precision(), 4)
        self.assertEqual(value.representative(), 5)      # 2^0 + 2^2

    def test_digit_notation_with_a_point(self):
        value = parse_p_adic('Q2:1.1010')
        self.assertEqual(value.precision(), 4)
        self.assertEqual(value.valuation(), -1)
        self.assertEqual(value.representative(), Fraction(11, 2))   # 2^-1 + 5

    def test_multi_digit_prime(self):
        #Digits are base-10 groups as wide as the prime: Q13:0102 is
        #13^-1 + 2*13^0 + O(13^1).
        value = parse_p_adic('Q13:01.02')
        self.assertEqual(value.prime(), 13)
        self.assertEqual(value.precision(), 1)
        self.assertEqual(value.representative(), Fraction(1, 13) + 2)

    def test_negative_digit_notation(self):
        self.assertEqual(parse_p_adic('Q3:-220').representative(),
                         -(2 + 2 * 3))

    def test_digit_notation_renders_back_unchanged(self):
        #Unlike the arithmetic spellings, this is a real presentation choice.
        for text in ['Q2:1010', 'Q2:1.1010', 'Q13:01.02', 'Q3:-220']:
            with self.subTest(text=text):
                self.assertEqual(parse_p_adic(text).render()[0], text)

    def test_rejects_undocumented_text(self):
        for text in ['', 'hello', '3 + O(2)', 'Q2:', '1 + O(2^5) extra']:
            with self.subTest(text=text):
                with self.assertRaises(ParseError):
                    parse_p_adic(text)


class TheDocumentationsOwnEquivalence(unittest.TestCase):
    """help.html declares two forms equivalent; that pins the convention.

        "3+1/2 + O(2^3)" represents the 2-adic ball 2^-1 + 2^0 + 2^1 + O(2^3)
        "Q2:1.110"       represents the 2-adic ball 2^-1 + 2^0 + 2^1 + O(2^3)

    3 + 1/2 = 7/2 = 2^-1 * 7, so the valuation is -1 and the stated precision is
    absolute. The digit form carries one digit before the point and three after
    -- four significant digits, at 2^-1 through 2^2. The two agree only if
    O(p^k) means "known modulo p^k" regardless of valuation, which is also the
    standard meaning of big-O in p-adic analysis.

    The Sage path fails this: it yields O(2^2) for the rational form and O(2^3)
    for the digit form, so the two documented-as-equivalent spellings come out
    at different precisions.
    """

    def test_the_two_documented_spellings_agree(self):
        rational = parse_p_adic('3+1/2 + O(2^3)')
        digits = parse_p_adic('Q2:1.110')
        self.assertEqual(rational, digits)
        self.assertEqual(rational.precision(), 3)
        self.assertEqual(digits.precision(), 3)

    def test_the_stated_value(self):
        value = parse_p_adic('3+1/2 + O(2^3)')
        self.assertEqual(value.representative(), Fraction(7, 2))
        self.assertEqual(value.valuation(), -1)
        #2^-1 + 2^0 + 2^1
        self.assertEqual(value.representative(),
                         Fraction(1, 2) + 1 + 2)

    def test_precision_is_absolute_not_relative(self):
        #Same value, precision stated three ways: the number of significant
        #digits changes with the valuation, the absolute precision does not.
        for text, expected_precision in [('3+1/2 + O(2^3)', 3),
                                         ('7 + O(2^3)', 3),
                                         ('2^-5 * 7 + O(2^3)', 3)]:
            with self.subTest(text=text):
                self.assertEqual(parse_p_adic(text).precision(), expected_precision)


class CorpusShapes(unittest.TestCase):
    """The four forms numberdb-data actually uses."""

    def test_plain_integer(self):
        value = parse_p_adic('80070539116894875484728262691342135225246161237805 + O(2^167)')
        self.assertEqual(value.prime(), 2)
        self.assertEqual(value.precision(), 167)
        self.assertEqual(value.valuation(), 0)

    def test_negative_power_times_integer(self):
        value = parse_p_adic('2^-1 * 184381557386107545205015127224797726430883097714031 + O(2^166)')
        self.assertEqual(value.valuation(), -1)
        self.assertEqual(value.precision(), 166)

    def test_coefficient_times_integer(self):
        value = parse_p_adic('3 * 37051644188163625629762074446120505244445039577578 + O(3^105)')
        self.assertEqual(value.prime(), 3)
        self.assertEqual(value.precision(), 105)

    def test_stated_precision_is_kept_for_negative_valuation(self):
        #Regression against the Sage path, which computed the working precision
        #as e + min(0, -valuation) -- always e when the valuation is negative,
        #where e - valuation is needed. It therefore lost |valuation| digits:
        #  2^-1 * N + O(2^166) came back with precision 165
        #  2^-2 * N + O(2^165)                          163
        #  2^-5 * N + O(2^162)                          157
        for text, expected in [
                ('2^-1 * 3 + O(2^166)', 166),
                ('2^-2 * 3 + O(2^165)', 165),
                ('2^-5 * 3 + O(2^162)', 162)]:
            with self.subTest(text=text):
                self.assertEqual(parse_p_adic(text).precision(), expected)


class Canonicalisation(unittest.TestCase):
    """Different spellings of one ball must compare equal, or dedup breaks."""

    def test_representatives_congruent_modulo_the_precision_are_equal(self):
        self.assertEqual(parse_p_adic('3 + O(2^5)'), parse_p_adic('35 + O(2^5)'))
        self.assertEqual(hash(parse_p_adic('3 + O(2^5)')),
                         hash(parse_p_adic('35 + O(2^5)')))

    def test_different_precision_is_a_different_ball(self):
        self.assertNotEqual(parse_p_adic('3 + O(2^5)'), parse_p_adic('3 + O(2^6)'))

    def test_different_prime_is_a_different_ball(self):
        self.assertNotEqual(parse_p_adic('3 + O(2^5)'), parse_p_adic('3 + O(3^5)'))

    def test_arithmetic_spellings_agree(self):
        self.assertEqual(parse_p_adic('2^-1 * 3 + O(2^5)'),
                         parse_p_adic('3/2 + O(2^5)'))

    def test_canonical_representative_is_reduced(self):
        value = parse_p_adic('35 + O(2^5)')
        self.assertEqual(value.canonical_representative(), 3)


class Containment(unittest.TestCase):
    """p-adic balls are nested or disjoint, never partially overlapping."""

    def test_coarser_ball_contains_finer_one(self):
        coarse = parse_p_adic('3 + O(2^3)')
        fine = parse_p_adic('3 + O(2^8)')
        self.assertTrue(coarse.contains(fine))
        self.assertFalse(fine.contains(coarse))
        self.assertTrue(coarse.overlaps(fine))
        self.assertTrue(fine.overlaps(coarse))

    def test_disjoint_balls(self):
        self.assertFalse(parse_p_adic('1 + O(2^4)')
                         .overlaps(parse_p_adic('2 + O(2^4)')))

    def test_different_primes_never_overlap(self):
        self.assertFalse(parse_p_adic('1 + O(2^4)')
                         .overlaps(parse_p_adic('1 + O(3^4)')))


class ExpressionEvaluator(unittest.TestCase):
    """Deliberately not eval: this runs on stored data in the web container."""

    def test_operator_precedence_and_associativity(self):
        self.assertEqual(parse_p_adic('2+3*4 + O(5^9)').representative(), 14)
        self.assertEqual(parse_p_adic('2^3^2 + O(5^9)').representative(), 512)
        self.assertEqual(parse_p_adic('(2+3)*4 + O(5^9)').representative(), 20)

    def test_division_is_exact(self):
        self.assertEqual(parse_p_adic('1/3 + O(5^9)').representative(),
                         Fraction(1, 3))

    def test_rejects_malformed_expressions(self):
        for text in ['2** + O(5^3)', '(2 + O(5^3)', '2/0 + O(5^3)',
                     'os.system + O(5^3)']:
            with self.subTest(text=text):
                with self.assertRaises(ParseError):
                    parse_p_adic(text)

    def test_no_dotted_digit(self):
        #The O-term already states the precision, so marking a digit as well
        #would say it twice.
        _, dots = parse_p_adic('3 + O(2^5)').render()
        self.assertEqual(dots, ())

    def test_prime_must_be_at_least_two(self):
        with self.assertRaises(ParseError):
            ExactPAdic(1, 0, 5)


class RoundTrip(unittest.TestCase):

    SAMPLES = ['3 + O(2^5)', 'O(2^167)', 'Q2:1010', 'Q2:1.1010', 'Q3:-220',
               '2^-1 * 3 + O(2^166)', '3/5 + O(5^1)']

    def test_render_parse_render_is_stationary(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                once, _ = parse_p_adic(text).render()
                twice, _ = parse_p_adic(once).render()
                self.assertEqual(once, twice)

    def test_value_survives_the_round_trip(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                original = parse_p_adic(text)
                rendered, _ = original.render()
                self.assertEqual(parse_p_adic(rendered), original)


if __name__ == '__main__':
    unittest.main()
