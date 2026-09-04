"""What the package writes for a zero-width interval, read back by the server."""
import sys
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/clients/python')

from fractions import Fraction

from numberdb import ComplexInterval, RealInterval
from numberdb._write import to_text
from utils.numbers import canonical_text
from utils.utils import parse_complex_interval

root = RealInterval(Fraction(-8660254037844387, 10 ** 16),
                    Fraction(-8660254037844386, 10 ** 16))
cases = [
	('declared exact  ', ComplexInterval(Fraction(3, 2), root)),
	('landed on a point', ComplexInterval(
		RealInterval(Fraction(3, 2), Fraction(3, 2)), root)),
	('both declared    ', ComplexInterval(2, -1)),
	('both points      ', ComplexInterval(RealInterval(2, 2),
	                                      RealInterval(-1, -1))),
]
for name, value in cases:
	written = to_text(value, digits=12)
	parsed = parse_complex_interval(written)
	print('%-18s %s' % (name, written))
	print('%-18s   searchable: %s   stored: %s'
	      % ('', parsed is not None, canonical_text(written)))
