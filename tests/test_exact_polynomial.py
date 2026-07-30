"""Tests for utils/numbers/polynomial.py.

No Sage, no Django, no database:

    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import ParseError, parse_polynomial  # noqa: E402


class CorpusAndDocumentedForms(unittest.TestCase):

    def test_cyclotomic_entries(self):
        for text in ['x - 1', 'x + 1', 'x^2 + x + 1', 'x^2 + 1',
                     'x^4 + x^3 + x^2 + x + 1', 'x^2 - x + 1']:
            with self.subTest(text=text):
                self.assertEqual(parse_polynomial(text).render()[0], text)

    def test_front_page_example(self):
        #"Enter polynomials over Q in arbitrary variables,
        # e.g. x^6+y^6-x^5*y^5+4*x*y"
        value = parse_polynomial('x^6+y^6-x^5*y^5+4*x*y')
        self.assertEqual(value.variables(), ('x', 'y'))
        self.assertEqual(value.degree(), 10)
        self.assertEqual(value.coefficients()[(('x', 5), ('y', 5))], -1)
        self.assertEqual(value.coefficients()[(('x', 1), ('y', 1))], 4)

    def test_rational_coefficients(self):
        value = parse_polynomial('1/384*x0^4*x1^4 + 17/96*x0^3*x1^3')
        self.assertEqual(value.coefficients()[(('x0', 4), ('x1', 4))],
                         Fraction(1, 384))
        self.assertEqual(value.coefficients()[(('x0', 3), ('x1', 3))],
                         Fraction(17, 96))

    def test_constants(self):
        self.assertEqual(parse_polynomial('1').degree(), 0)
        self.assertEqual(parse_polynomial('-2*x').degree(), 1)
        self.assertTrue(parse_polynomial('0').is_zero())
        self.assertEqual(parse_polynomial('0').degree(), -1)

    def test_decimal_coefficients_are_refused(self):
        #Would need an interval coefficient, which is a different type.
        with self.assertRaises(ParseError):
            parse_polynomial('0.5*x')

    def test_rejects_non_polynomials(self):
        for text in ['', 'x^', '(x+1', 'x^-1', 'x/y', '1/0*x']:
            with self.subTest(text=text):
                with self.assertRaises(ParseError):
                    parse_polynomial(text)


class VariableNamesAreKept(unittest.TestCase):
    """The Sage path rebuilds in PolynomialRing(QQ, n, 'x'), losing them.

    The Gegenbauer table is written `2*a*x` -- `a` the parameter, `x` the
    variable -- and the current implementation displays `2*x0*x1`.
    """

    def test_names_survive_the_round_trip(self):
        for text in ['2*a*x', 'x^6 + y^6', 'a^2*b + b^2*c']:
            with self.subTest(text=text):
                value = parse_polynomial(text)
                self.assertEqual(parse_polynomial(value.render()[0]), value)
                for name in value.variables():
                    self.assertIn(name, value.render()[0])

    def test_gegenbauer_entry_is_not_renamed(self):
        rendered, _ = parse_polynomial('2*a*x').render()
        self.assertEqual(rendered, '2*a*x')
        self.assertNotIn('x0', rendered)


class RenamingInvariance(unittest.TestCase):
    """Search must match across names; display must not conflate them."""

    def test_same_shape_different_names_share_a_search_key(self):
        first = parse_polynomial('x^2+1')
        second = parse_polynomial('y^2+1')
        self.assertNotEqual(first, second)
        self.assertEqual(first.canonical_under_renaming(),
                         second.canonical_under_renaming())

    def test_permuted_variables_share_a_search_key(self):
        self.assertEqual(parse_polynomial('x^2*y').canonical_under_renaming(),
                         parse_polynomial('y^2*x').canonical_under_renaming())

    def test_genuinely_different_polynomials_do_not(self):
        self.assertNotEqual(parse_polynomial('x^2+1').canonical_under_renaming(),
                            parse_polynomial('x^3+1').canonical_under_renaming())

    def test_too_many_variables_is_refused_rather_than_attempted(self):
        #The key is factorial in the number of variables.
        many = '*'.join('v%d' % i for i in range(8))
        with self.assertRaises(ParseError):
            parse_polynomial(many).canonical_under_renaming()


class Arithmetic(unittest.TestCase):

    def test_expansion_and_collection(self):
        self.assertEqual(parse_polynomial('(x+1)^2'),
                         parse_polynomial('x^2+2*x+1'))

    def test_cancellation(self):
        self.assertTrue(parse_polynomial('x - x').is_zero())
        self.assertEqual(parse_polynomial('x + x'), parse_polynomial('2*x'))

    def test_division_by_a_constant_only(self):
        self.assertEqual(parse_polynomial('x/2'), parse_polynomial('1/2*x'))
        with self.assertRaises(ParseError):
            parse_polynomial('x/y')

    def test_equality_ignores_term_order(self):
        self.assertEqual(parse_polynomial('1 + x'), parse_polynomial('x + 1'))
        self.assertEqual(hash(parse_polynomial('1 + x')),
                         hash(parse_polynomial('x + 1')))

    def test_no_dotted_digit(self):
        _, dots = parse_polynomial('x^2 + 1').render()
        self.assertEqual(dots, ())


class RoundTrip(unittest.TestCase):

    SAMPLES = ['x - 1', 'x^2 + x + 1', '2*a*x', '-2*x', '1', '0',
               'x^6+y^6-x^5*y^5+4*x*y', '1/384*x0^4*x1^4 - 1/96*x0^3']

    def test_render_parse_render_is_stationary(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                once, _ = parse_polynomial(text).render()
                twice, _ = parse_polynomial(once).render()
                self.assertEqual(once, twice)

    def test_value_survives_the_round_trip(self):
        for text in self.SAMPLES:
            with self.subTest(text=text):
                original = parse_polynomial(text)
                self.assertEqual(parse_polynomial(original.render()[0]), original)


if __name__ == '__main__':
    unittest.main()
