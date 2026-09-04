"""What the package writes for a mixed complex value, read back by the server."""
import os
import sys

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/clients/python')

from fractions import Fraction

from numberdb import ComplexInterval, RealInterval
from numberdb._write import to_text
from utils.numbers import ParseError, canonical_text
from utils.utils import parse_complex_interval

sqrt3 = RealInterval(Fraction(-8660254037844387, 10 ** 16),
                     Fraction(-8660254037844386, 10 ** 16))
cases = [
	('both exact', ComplexInterval(2, -1)),
	('T35: (3+i*sqrt3)/2', ComplexInterval(Fraction(3, 2), sqrt3)),
	('5/65 + an interval', ComplexInterval(Fraction(5, 65), sqrt3)),
	('neither exact', ComplexInterval(sqrt3, sqrt3)),
]
for name, value in cases:
	written = to_text(value, digits=12)
	parsed = parse_complex_interval(written)
	try:
		canonical = canonical_text(written)
	except ParseError as bad:
		canonical = 'ParseError: %s' % (bad,)
	print('%-20s %s' % (name, written))
	print('%-20s parsed: re exact=%s im exact=%s'
	      % ('', parsed.real().is_exact(), parsed.imag().is_exact()))
	print('%-20s stored: %s' % ('', canonical))
