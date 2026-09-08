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
	"""(degree, terms) for canonical polynomial text, or (None, None).

	`Polynomial.number_string` is "<variables>,<polynomial>"; this accepts
	either that or the polynomial alone.
	"""
	body = (text or '').strip()
	if not body:
		return None, None
	if ',' in body[:4] and body.split(',', 1)[0].strip().isdigit():
		body = body.split(',', 1)[1]
	powers = [int(match) for match in _POWER.findall(body)]
	#Terms: the top-level summands. Canonical text separates them with a
	#spaced sign, so a negative exponent or a sign inside a coefficient does
	#not split a term in two.
	terms = len(re.split(r'\s[-+]\s', body.strip()))
	if powers:
		degree = max(powers)
	elif _VARIABLE.search(body):
		degree = 1
	else:
		degree = 0
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
