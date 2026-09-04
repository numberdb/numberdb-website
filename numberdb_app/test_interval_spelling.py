"""An explicit interval may have rational endpoints.

The exact layer accepts `[3/2, 3/2]` and stores it faithfully. The search
parser did not: `RIF('3/2')` raises, so the whole value was refused and the
row was never indexed. A number written that way sat on its page and could
not be found by its digits, which is the shape of fault that once hid 101 of
them.

This matters now because a zero-width interval is written as an interval --
`[3/2, 3/2]`, not `3/2` -- so that the page says which of the two things it
is: a value declared exact, or interval arithmetic that landed on a point.
Both assert the same number; only one is a rational.
"""

from django.test import SimpleTestCase

from utils.utils import parse_complex_interval, parse_real_interval


class AnIntervalMayHaveRationalEndpoints(SimpleTestCase):

	def test_a_rational_endpoint_is_read(self):
		value = parse_real_interval('[3/2, 3/2]')
		self.assertIsNotNone(value)
		self.assertEqual(value.lower(), 1.5)
		self.assertEqual(value.upper(), 1.5)

	def test_a_genuine_range_of_rationals(self):
		value = parse_real_interval('[1/3, 1/2]')
		self.assertIsNotNone(value)
		self.assertLess(value.lower(), value.upper())
		self.assertLess(float(value.lower()), 0.34)
		self.assertGreater(float(value.upper()), 0.49)

	def test_decimal_endpoints_still_work(self):
		self.assertIsNotNone(parse_real_interval('[1.5, 1.5]'))
		self.assertIsNotNone(parse_real_interval('[2, 2]'))

	def test_a_nonsense_endpoint_is_still_refused(self):
		self.assertIsNone(parse_real_interval('[3/2, banana]'))
		self.assertIsNone(parse_real_interval('[1/0, 2]'))

	def test_the_complex_composite_is_read(self):
		#The spelling a mixed complex value is written in.
		value = parse_complex_interval('[3/2, 3/2] + i * -0.866025403784')
		self.assertIsNotNone(value)
		self.assertEqual(value.real().lower(), 1.5)
		self.assertLess(value.imag().upper(), 0)

	def test_a_rational_component_beside_an_interval_one(self):
		value = parse_complex_interval('3/2 + i * -0.866025403784')
		self.assertIsNotNone(value)
		self.assertTrue(value.real().is_exact())
		self.assertFalse(value.imag().is_exact())

	def test_both_layers_agree_on_what_is_writable(self):
		#The asymmetry this closes: the exact layer kept these and the search
		#layer dropped them, so a value could be stored and not indexed.
		from utils.numbers import canonical_text

		for text in ('[3/2, 3/2]', '[2, 2]', '[1/3, 1/2]',
		             '[3/2, 3/2] + i * -0.866025403784'):
			self.assertIsNotNone(canonical_text(text), text)
			self.assertIsNotNone(parse_complex_interval(text), text)
