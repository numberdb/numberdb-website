"""Exact representation of the p-adic numbers NumberDB stores.

A p-adic entry denotes a **ball** ``a + p^k Z_p``: a rational representative and
a precision. That is already how the data is written --
``80070539... + O(2^167)`` -- so unlike the real case there is no float layer to
undo, only a Sage dependency to remove.

Where reals needed several notations because they carry different information
(``3.14`` and ``3.140`` denote different intervals), the p-adic representative
forms in the corpus are merely arithmetic spellings of one rational:

    integer + O(p^k)              4856 entries
    p^e * integer + O(p^k)        1122
    c * integer + O(p^k)           714
    O(p^k)                          20

So they are evaluated to a single canonical form rather than preserved
separately. Nothing is lost: ``2^-1 * 3`` and ``3/2`` are the same number, which
was not true of ``3.14`` and ``3.140``.

The digit notation (``Q2:1.1010``) *is* a genuinely different presentation of
the same ball, so which one was used is remembered.

Evaluating the representative needs arithmetic over the rationals, which is why
there is a small expression parser here. The Sage implementation used
``eval(preparse(a))`` -- fine inside the evaluator sandbox, not something to
run in the web container on stored data.
"""

import re
from fractions import Fraction

from .real import ParseError

__all__ = ['ExactPAdic', 'parse_p_adic']


# --------------------------------------------------------------------------
# a small rational expression evaluator
# --------------------------------------------------------------------------

_TOKEN = re.compile(r'\s*(\d+|[-+*/^()])')


def _tokenize(text):
    tokens = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            if text[position].isspace():
                position += 1
                continue
            raise ParseError('unexpected character %r in %r' % (text[position], text))
        tokens.append(match.group(1))
        position = match.end()
    return tokens


class _Expression:
    """Recursive descent over integers with + - * / ^ and parentheses.

    Deliberately not ``eval``: this runs on stored data in the web container,
    and the grammar it needs is four operators wide.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def peek(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self):
        token = self.peek()
        self.position += 1
        return token

    def parse(self):
        value = self.sum()
        if self.position != len(self.tokens):
            raise ParseError('trailing input at %r' % (self.peek(),))
        return value

    def sum(self):
        value = self.product()
        while self.peek() in ('+', '-'):
            operator = self.take()
            right = self.product()
            value = value + right if operator == '+' else value - right
        return value

    def product(self):
        value = self.power()
        while self.peek() in ('*', '/'):
            operator = self.take()
            right = self.power()
            if operator == '/':
                if right == 0:
                    raise ParseError('division by zero')
                value = value / right
            else:
                value = value * right
        return value

    def power(self):
        base = self.atom()
        if self.peek() == '^':
            self.take()
            exponent = self.power()          # right associative
            if exponent.denominator != 1:
                raise ParseError('fractional exponent')
            return base ** int(exponent)
        return base

    def atom(self):
        token = self.take()
        if token is None:
            raise ParseError('unexpected end of expression')
        if token == '-':
            return -self.atom()
        if token == '+':
            return self.atom()
        if token == '(':
            value = self.sum()
            if self.take() != ')':
                raise ParseError('unbalanced parenthesis')
            return value
        if token.isdigit():
            return Fraction(int(token))
        raise ParseError('unexpected token %r' % (token,))


def _evaluate(text):
    return _Expression(_tokenize(text)).parse()


# --------------------------------------------------------------------------
# p-adic arithmetic
# --------------------------------------------------------------------------

def _valuation(value, prime):
    """The p-adic valuation of a non-zero rational."""
    numerator, denominator = value.numerator, value.denominator
    valuation = 0
    while numerator % prime == 0:
        numerator //= prime
        valuation += 1
    while denominator % prime == 0:
        denominator //= prime
        valuation -= 1
    return valuation


def _canonical(representative, prime, precision):
    """A canonical representative of the ball ``representative + p^k Z_p``.

    Two spellings of the same ball must reduce to the same value, or equality
    and dedup silently break.
    """
    if representative == 0:
        return Fraction(0)
    valuation = _valuation(representative, prime)
    if precision <= valuation:
        # The ball already contains 0.
        return Fraction(0)
    unit = representative / Fraction(prime) ** valuation
    modulus = prime ** (precision - valuation)
    residue = (unit.numerator * pow(unit.denominator, -1, modulus)) % modulus
    return Fraction(residue) * Fraction(prime) ** valuation


class ExactPAdic:
    """A p-adic ball: a rational representative to a stated precision."""

    __slots__ = ('_prime', '_representative', '_precision', '_digits_form')

    def __init__(self, prime, representative, precision, digits_form=None):
        if prime < 2:
            raise ParseError('prime must be at least 2')
        self._prime = int(prime)
        self._representative = Fraction(representative)
        self._precision = int(precision)
        #Set when the value was written in Q-notation, so it renders back that
        #way. Unlike the arithmetic spellings, that is a real presentation
        #choice rather than a different way of writing the same sum.
        self._digits_form = digits_form

    def prime(self):
        return self._prime

    def precision(self):
        return self._precision

    def representative(self):
        return self._representative

    def valuation(self):
        if self._representative == 0:
            return self._precision
        return _valuation(self._representative, self._prime)

    def canonical_representative(self):
        return _canonical(self._representative, self._prime, self._precision)

    def contains(self, other):
        """True if this ball contains ``other``'s.

        A ball contains another when it is no more precise and their
        representatives agree to this ball's precision.
        """
        if self._prime != other.prime():
            return False
        if self._precision > other.precision():
            return False
        difference = self._representative - other.representative()
        if difference == 0:
            return True
        return _valuation(difference, self._prime) >= self._precision

    def overlaps(self, other):
        """p-adic balls are nested or disjoint, never partially overlapping."""
        return self.contains(other) or other.contains(self)

    def render(self):
        """(text, dotted_indices).

        Indices are always empty: a p-adic ball states its precision explicitly
        with the O-term, so there is no uncertain digit to mark.
        """
        if self._digits_form is not None:
            return (self._digits_form, ())

        representative = self.canonical_representative()
        if representative == 0:
            return ('O(%d^%d)' % (self._prime, self._precision), ())

        valuation = _valuation(representative, self._prime)
        if valuation < 0:
            #Matches how the corpus writes these: p^-1 * N rather than N/p.
            unit = representative / Fraction(self._prime) ** valuation
            text = '%d^%d * %s + O(%d^%d)' % (
                self._prime, valuation, unit, self._prime, self._precision)
        else:
            text = '%s + O(%d^%d)' % (representative, self._prime, self._precision)
        return (text, ())

    def __eq__(self, other):
        if not isinstance(other, ExactPAdic):
            return NotImplemented
        return (self._prime == other.prime()
                and self._precision == other.precision()
                and self.canonical_representative() == other.canonical_representative())

    def __hash__(self):
        return hash((self._prime, self._precision, self.canonical_representative()))

    def __repr__(self):
        return 'ExactPAdic(%s)' % (self.render()[0],)

    def __str__(self):
        return self.render()[0]


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_BIG_OH = re.compile(r'^(.*?)\+?\s*O\((\d+)\^(-?\d+)\)$')
_DIGITS = re.compile(r'^[qQzZ](\d+)[: ](-?)((?:\d*\.)?)(\d*)$')


def _parse_digit_notation(text):
    match = _DIGITS.match(text)
    if not match:
        return None
    prime_text, sign, before_point, after_point = match.groups()
    if before_point.endswith('.'):
        before_point = before_point[:-1]
    if not before_point and not after_point:
        raise ParseError('digit notation with no digits')
    prime = int(prime_text)
    width = len(prime_text)
    if len(before_point) % width or len(after_point) % width:
        raise ParseError('digit groups do not match the width of %d' % (prime,))

    def digits_of(chunk):
        return [int(chunk[i:i + width]) for i in range(0, len(chunk), width)]

    #Leftmost digit is the p^0 place -- "most significant" in the p-adic sense
    #of largest absolute value.
    value = Fraction(0)
    negative_digits = digits_of(before_point)
    for index, digit in enumerate(negative_digits):
        value += Fraction(digit) * Fraction(prime) ** (index - len(negative_digits))
    for index, digit in enumerate(digits_of(after_point)):
        value += Fraction(digit) * Fraction(prime) ** index
    if sign == '-':
        value = -value
    precision = len(after_point) // width
    return ExactPAdic(prime, value, precision, digits_form=text)


def parse_p_adic(text):
    """Parse the documented p-adic formats into an ``ExactPAdic``.

        3 + O(2^5)                  rational representative
        2^0+2^1+O(2^5)              as an expression
        2^-1 * 1843... + O(2^166)   as written in numberdb-data
        3/5 + O(5^1)                rational
        O(2^167)                    zero to a stated precision
        Q2:1.1010                   digit notation
    """
    if not isinstance(text, str):
        raise ParseError('expected text')
    stripped = text.strip()
    if not stripped:
        raise ParseError('empty')

    digits = _parse_digit_notation(stripped.replace(' ', ''))
    if digits is not None:
        return digits

    match = _BIG_OH.match(stripped.replace(' ', ''))
    if not match:
        raise ParseError('not a documented p-adic format: %r' % (text,))

    representative_text, prime_text, precision_text = match.groups()
    prime = int(prime_text)
    precision = int(precision_text)
    representative = (_evaluate(representative_text)
                      if representative_text else Fraction(0))
    return ExactPAdic(prime, representative, precision)
