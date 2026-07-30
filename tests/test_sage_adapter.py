"""Tests for utils/numbers/sage_adapter.py.

These need SageMath and are skipped without it, so the plain-Python suite still
passes on a machine that has no Sage:

    python3 -m unittest discover -s tests          # skipped
    sage -python -m unittest discover -s tests     # exercised

The separation is the point: everything else in utils/numbers is tested without
Sage, and only this boundary requires it.
"""

import os
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import parse_complex, parse_real  # noqa: E402

try:
    from sage.rings.all import RealIntervalField, ComplexIntervalField
    from utils.numbers import sage_adapter
    HAVE_SAGE = True
except ImportError:
    HAVE_SAGE = False


def exact(endpoint):
    """Sage real endpoint -> Fraction.

    Sage's Rational exposes numerator/denominator as *methods*, so comparing
    one directly with a Fraction raises rather than returning False -- a trap
    worth keeping in one place.
    """
    rational = endpoint.exact_rational()
    return Fraction(int(rational.numerator()), int(rational.denominator()))


@unittest.skipUnless(HAVE_SAGE, 'SageMath not available')
class ToSageIsLossyButSound(unittest.TestCase):
    """Binary cannot hold 313/100, so the interval must widen, never narrow."""

    SAMPLES = ['3.14', '5/6', '1/6', '12e2', '[2, 2.3728596]',
               '3.14 +/- 2e-2', '0.001', '-1.5e-3', '1/3', '42']

    def test_interval_contains_the_exact_bounds(self):
        for source in self.SAMPLES:
            with self.subTest(source=source):
                value = parse_real(source)
                low, high = value.bounds()
                element = sage_adapter.to_real_interval(value)
                self.assertLessEqual(exact(element.lower()), low,
                                     'lower endpoint moved inward')
                self.assertGreaterEqual(exact(element.upper()), high,
                                        'upper endpoint moved inward')

    def test_ball_contains_the_exact_bounds(self):
        for source in self.SAMPLES:
            with self.subTest(source=source):
                value = parse_real(source)
                low, high = value.bounds()
                ball = sage_adapter.to_real_ball(value)
                interval = RealIntervalField(1000)(ball)
                self.assertLessEqual(exact(interval.lower()), low)
                self.assertGreaterEqual(exact(interval.upper()), high)

    def test_complex_box_contains_the_exact_box(self):
        for source in ['5/6 + 5.5I', '-1/2 + i*0.86602', '1/3+1/7*I']:
            with self.subTest(source=source):
                value = parse_complex(source)
                (re_low, re_high), (im_low, im_high) = value.bounds()
                element = sage_adapter.to_complex_interval(value)
                self.assertLessEqual(exact(element.real().lower()), re_low)
                self.assertGreaterEqual(exact(element.real().upper()), re_high)
                self.assertLessEqual(exact(element.imag().lower()), im_low)
                self.assertGreaterEqual(exact(element.imag().upper()), im_high)

    def test_exact_values_stay_exact_enough_to_contain_themselves(self):
        value = parse_real('5/6')
        element = sage_adapter.to_real_interval(value)
        self.assertLessEqual(exact(element.lower()), Fraction(5, 6))
        self.assertGreaterEqual(exact(element.upper()), Fraction(5, 6))


@unittest.skipUnless(HAVE_SAGE, 'SageMath not available')
class FromSageIsExact(unittest.TestCase):
    """Sage interval endpoints are dyadic, hence rational: nothing is lost."""

    def test_endpoints_come_back_exactly(self):
        field = RealIntervalField(53)
        element = field(1) / field(3)
        value = sage_adapter.from_real_interval(element)
        low, high = value.bounds()
        self.assertEqual(low, exact(element.lower()))
        self.assertEqual(high, exact(element.upper()))

    def test_round_trip_through_sage_never_narrows(self):
        #to_sage widens, from_sage is exact, so the composition must contain
        #the original -- the property the search index depends on.
        for source in ['3.14', '5/6', '1/6', '12e2', '[2, 2.3728596]']:
            with self.subTest(source=source):
                original = parse_real(source)
                low, high = original.bounds()
                returned = sage_adapter.from_real_interval(
                    sage_adapter.to_real_interval(original))
                returned_low, returned_high = returned.bounds()
                self.assertLessEqual(returned_low, low)
                self.assertGreaterEqual(returned_high, high)

    def test_complex_round_trip_never_narrows(self):
        for source in ['5/6 + 5.5I', '3.14-2.71*I']:
            with self.subTest(source=source):
                original = parse_complex(source)
                (re_low, re_high), (im_low, im_high) = original.bounds()
                returned = sage_adapter.from_complex_interval(
                    sage_adapter.to_complex_interval(original))
                (got_re_low, got_re_high), (got_im_low, got_im_high) = returned.bounds()
                self.assertLessEqual(got_re_low, re_low)
                self.assertGreaterEqual(got_re_high, re_high)
                self.assertLessEqual(got_im_low, im_low)
                self.assertGreaterEqual(got_im_high, im_high)

    def test_result_renders_in_a_documented_format(self):
        field = ComplexIntervalField(53)
        element = field(field(1) / field(3), field(1) / field(7))
        rendered, _ = sage_adapter.from_complex_interval(element).render()
        self.assertIn('*I', rendered)
        self.assertTrue(rendered.startswith('['))


class TheExactLayerDoesNotNeedSage(unittest.TestCase):
    """Guards the architectural boundary this module exists to keep."""

    def test_importing_utils_numbers_does_not_import_sage(self):
        #Run in a clean interpreter: importing the exact layer must not pull
        #SageMath in, or the web container gains it back by the side door.
        import subprocess
        code = ('import sys; import utils.numbers; '
                'print("sage" in sys.modules or '
                'any(m.startswith("sage.") for m in sys.modules))')
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run([sys.executable, '-c', code], cwd=root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'False',
                         'utils.numbers pulled Sage in')


if __name__ == '__main__':
    unittest.main()
