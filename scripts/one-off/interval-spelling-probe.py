"""Does the database read an explicit interval, and a complex one with a part like that?"""
import sys
sys.path.insert(0, '/app')
from utils.numbers import ParseError, canonical_text
from utils.utils import parse_complex_interval, parse_real_interval

cases = ['[3/2, 3/2]', '[2, 2]', '[1.5, 1.5]', '3/2 +/- 0',
         '[3/2, 3/2] + i * -0.866025403784',
         '[2, 2] + i * -1']
for s in cases:
	real = None
	try:
		real = parse_real_interval(s)
	except Exception as e:
		real = 'raised %s' % type(e).__name__
	comp = None
	try:
		comp = parse_complex_interval(s)
	except Exception as e:
		comp = 'raised %s' % type(e).__name__
	try:
		canon = canonical_text(s)
	except ParseError as bad:
		canon = 'ParseError'
	except Exception as e:
		canon = '%s' % type(e).__name__
	print('%-36s real=%-22s complex=%-24s exact=%s'
	      % (s, str(real)[:22], str(comp)[:24], canon))
