"""How big a table's values are, measured from the values themselves.

The overview asks how much a table holds, and "entries" is only half of it:
a hundred Fibonacci polynomials and a hundred hundred-digit constants are the
same count and not the same table. So each kind is measured in the unit that
means something for it -- digits for a number, degree and terms for a
polynomial, precision for a p-adic -- and every kind also in characters,
which is the one measure they share and the one a reader feels.

Measured from the stored text rather than by parsing with Sage. Parsing 60000
entries to learn their degree costs minutes and answers the same question:
these are statistics, and a regular expression that is right on canonical text
is enough. Where it cannot tell, it returns None rather than a number.
"""
import re

#: `3.14159...`, `-0.5`, `1.23e-4`. The first run of digits after an optional
#: sign, which for an interval `[a, b]` or a ball `x +/- y` is the value
#: itself rather than its width.
_NUMBER = re.compile(r'-?\d[\d]*(?:\.\d+)?(?:[eE][-+]?\d+)?')

#: `O(2^167)`, `O(3^105)`.
_PADIC = re.compile(r'O\((\d+)\^(-?\d+)\)')

#: `x^12`, `a^3`. A bare variable is degree one and matches nothing here.
_POWER = re.compile(r'\^\s*(\d+)')

#: A variable: a letter not part of a function name. Canonical polynomial text
#: from this corpus uses single letters -- x, y, a, t.
_VARIABLE = re.compile(r'(?<![A-Za-z])[a-zA-Z](?![A-Za-z])')


def significant_digits(text):
	"""How many digits the value is written to, or None.

	The first number in the text: for `[1.41, 1.42]` that is the lower end,
	which has the same length as the upper, and for `3.14 +/- 2e-2` it is the
	centre rather than the radius.
	"""
	found = _NUMBER.search(text or '')
	if not found:
		return None
	digits = re.sub(r'[^0-9]', '', found.group(0).split('e')[0].split('E')[0])
	#A leading zero before the point is a placeholder, not a digit known.
	return len(digits.lstrip('0')) or len(digits)


def p_adic_digits(text):
	"""Precision in decimal digits: k for O(p^k), weighted by log10 p.

	A number known to O(2^167) and one known to O(3^105) are not comparable by
	k alone -- the second carries more information per digit -- so the unit
	here is the one they share.
	"""
	import math

	found = _PADIC.search(text or '')
	if not found:
		return None
	prime, power = int(found.group(1)), int(found.group(2))
	if prime < 2:
		return None
	return int(round(power * math.log10(prime)))


def polynomial_shape(text):
	"""(total degree, number of terms) for a stored polynomial, or (None, None).

	`Polynomial.number_string` is the canonical form the search index uses:

	    <variables>;<coefficient>:<monomial>|<coefficient>:<monomial>|...

	with each monomial a comma-separated list of `x<i>^<e>`, and an empty
	monomial for the constant term:

	    1;-1/1:|1/1:x0^1                           is  -1 + x
	    5;6/1:x0^1,x1^1|15/1:x2^1,x3^1|10/1:x4^2   is  6ab + 15cd + 10e^2

	Terms are the parts between the bars; the degree of a term is the sum of
	its exponents, and the polynomial's is the largest of those. Written for
	this format rather than for readable text, because the readable form is
	rendered from the document and never stored.
	"""
	body = (text or '').strip()
	if not body or ';' not in body:
		return None, None
	body = body.split(';', 1)[1]
	if not body:
		return 0, 0
	degree = 0
	terms = 0
	for term in body.split('|'):
		terms += 1
		monomial = term.split(':', 1)[1] if ':' in term else ''
		total = 0
		for factor in monomial.split(','):
			if '^' in factor:
				try:
					total += int(factor.rsplit('^', 1)[1])
				except ValueError:
					pass
		degree = max(degree, total)
	return degree, terms


def quartiles(values):
	"""(minimum, first quartile, median, third quartile, maximum, mean).

	Nearest-rank, which is what a reader of a table of integers expects: the
	median of four tables is one of them, not the average of the middle two.
	Empty gives None.
	"""
	ordered = sorted(v for v in values if v is not None)
	if not ordered:
		return None
	def rank(fraction):
		position = max(0, min(len(ordered) - 1,
		                      int(round(fraction * (len(ordered) - 1)))))
		return ordered[position]
	return {
		'min': ordered[0],
		'q1': rank(0.25),
		'median': rank(0.5),
		'q3': rank(0.75),
		'max': ordered[-1],
		'mean': sum(ordered) / float(len(ordered)),
		'count': len(ordered),
	}
