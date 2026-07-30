"""Exact representation of the polynomials NumberDB stores.

Polynomials are the one type that was already exact -- coefficients are
rationals and ``parse_polynomial`` rejects a decimal point outright -- so this
module is about removing the Sage dependency and keeping what the contributor
wrote, not about recovering lost precision.

Two things it fixes.

**Variable names survive.** The Sage path rebuilds every polynomial in
``PolynomialRing(QQ, n, 'x')``, so a multivariate entry comes back named
``x0, x1, ...``. The Gegenbauer table is written ``2*a*x`` -- ``a`` the
parameter, ``x`` the variable -- and displays as ``2*x0*x1``, which is both
less readable and less true. Here the names are kept.

**Renaming-invariance becomes explicit.** Search should match ``x^2+1`` against
``y^2+1``, so the old code normalised names *into the stored value*, conflating
"how it is written" with "how it is looked up". Here the stored value keeps its
names and ``canonical_under_renaming()`` provides the search key separately --
the same split as bounds versus search bounds for reals.

That key is computed with ``itertools.permutations`` rather than Sage's
``SymmetricGroup``, which was one of only two places the web container needed
Sage's group theory at all.
"""

import itertools
import re
from fractions import Fraction

from .real import ParseError

__all__ = ['ExactPolynomial', 'parse_polynomial']

#: Guard on the renaming-invariant key: n! permutations is fine for the two or
#: three variables that occur in practice and must not be attempted for many.
MAX_VARIABLES_FOR_CANONICAL_FORM = 6


# --------------------------------------------------------------------------
# monomial arithmetic
# --------------------------------------------------------------------------

def _multiply(left, right):
    product = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            monomial = dict(left_monomial)
            for variable, exponent in right_monomial:
                monomial[variable] = monomial.get(variable, 0) + exponent
            key = tuple(sorted(monomial.items()))
            product[key] = product.get(key, 0) + left_coefficient * right_coefficient
    return {k: v for k, v in product.items() if v != 0}


def _add(left, right, sign=1):
    total = dict(left)
    for monomial, coefficient in right.items():
        total[monomial] = total.get(monomial, 0) + sign * coefficient
    return {k: v for k, v in total.items() if v != 0}


def _scale(polynomial, factor):
    if factor == 0:
        return {}
    return {k: v * factor for k, v in polynomial.items()}


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_TOKEN = re.compile(r'\s*(\d+|[A-Za-z]\w*|[-+*/^()])')


def _tokenize(text):
    tokens = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            if text[position].isspace():
                position += 1
                continue
            raise ParseError('unexpected character %r in %r'
                             % (text[position], text))
        tokens.append(match.group(1))
        position = match.end()
    return tokens


class _Parser:
    """Recursive descent producing a monomial dictionary.

    Not ``eval``: this runs in the web container over stored data.
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
            value = _add(value, self.product(), 1 if operator == '+' else -1)
        return value

    def product(self):
        value = self.power()
        while self.peek() in ('*', '/'):
            operator = self.take()
            right = self.power()
            if operator == '*':
                value = _multiply(value, right)
            else:
                #Division only by a non-zero constant: the result must stay a
                #polynomial, and 1/384*x^4 is how the corpus writes rational
                #coefficients.
                if list(right.keys()) != [()]:
                    raise ParseError('can only divide by a constant')
                divisor = right[()]
                if divisor == 0:
                    raise ParseError('division by zero')
                value = _scale(value, Fraction(1, 1) / divisor)
        return value

    def power(self):
        base = self.atom()
        if self.peek() == '^':
            self.take()
            exponent = self.atom()
            if list(exponent.keys()) != [()] or exponent[()].denominator != 1:
                raise ParseError('exponent must be an integer')
            count = int(exponent[()])
            if count < 0:
                raise ParseError('negative exponent is not a polynomial')
            result = {(): Fraction(1)}
            for _ in range(count):
                result = _multiply(result, base)
            return result
        return base

    def atom(self):
        token = self.take()
        if token is None:
            raise ParseError('unexpected end of expression')
        if token == '-':
            return _scale(self.atom(), -1)
        if token == '+':
            return self.atom()
        if token == '(':
            value = self.sum()
            if self.take() != ')':
                raise ParseError('unbalanced parenthesis')
            return value
        if token.isdigit():
            return {(): Fraction(int(token))}
        if token[0].isalpha():
            return {((token, 1),): Fraction(1)}
        raise ParseError('unexpected token %r' % (token,))


def parse_polynomial(text):
    """Parse a polynomial over the rationals.

    Documented on the front page as "polynomials over Q in arbitrary
    variables", e.g. ``x^6+y^6-x^5*y^5+4*x*y``. The corpus also writes
    rational coefficients as ``1/384*x0^4*x1^4`` and parameters by name, as in
    ``2*a*x``.
    """
    if not isinstance(text, str):
        raise ParseError('expected text')
    stripped = text.strip()
    if not stripped:
        raise ParseError('empty')
    if '.' in stripped:
        #Only exact coefficients: a decimal point would need an interval
        #coefficient, which is a different type.
        raise ParseError('decimal coefficients are not supported')
    terms = _Parser(_tokenize(stripped)).parse()
    return ExactPolynomial(terms)


# --------------------------------------------------------------------------
# the value
# --------------------------------------------------------------------------

class ExactPolynomial:
    """A polynomial with exact rational coefficients, keeping its variables."""

    __slots__ = ('_terms',)

    def __init__(self, terms):
        self._terms = {monomial: Fraction(coefficient)
                       for monomial, coefficient in terms.items()
                       if coefficient != 0}

    def variables(self):
        names = set()
        for monomial in self._terms:
            for variable, _ in monomial:
                names.add(variable)
        return tuple(sorted(names))

    def degree(self):
        if not self._terms:
            return -1
        return max(sum(exponent for _, exponent in monomial)
                   for monomial in self._terms)

    def coefficients(self):
        return dict(self._terms)

    def is_zero(self):
        return not self._terms

    def canonical_under_renaming(self):
        """A key equal for polynomials that differ only by variable names.

        Used for search, not for storage: ``x^2+1`` and ``y^2+1`` should find
        each other, but they are not the same text and should not display
        identically.

        Beyond MAX_VARIABLES_FOR_CANONICAL_FORM the permutation search is
        refused rather than run, since it is factorial.
        """
        names = self.variables()
        if len(names) > MAX_VARIABLES_FOR_CANONICAL_FORM:
            raise ParseError('too many variables for a renaming-invariant key')

        best = None
        for permutation in itertools.permutations(range(len(names))):
            mapping = {name: 'x%d' % permutation[index]
                       for index, name in enumerate(names)}
            renamed = tuple(sorted(
                (tuple(sorted((mapping[v], e) for v, e in monomial)), coefficient)
                for monomial, coefficient in self._terms.items()))
            if best is None or renamed < best:
                best = renamed
        return best

    def render(self):
        """(text, dotted_indices).

        Indices are always empty: coefficients are exact, so no digit is
        uncertain.
        """
        if not self._terms:
            return ('0', ())

        def sort_key(item):
            monomial, _ = item
            return (-sum(exponent for _, exponent in monomial),
                    tuple(sorted(monomial)))

        pieces = []
        for monomial, coefficient in sorted(self._terms.items(), key=sort_key):
            factors = []
            magnitude = abs(coefficient)
            if not monomial or magnitude != 1:
                factors.append(str(magnitude))
            for variable, exponent in sorted(monomial):
                factors.append(variable if exponent == 1
                               else '%s^%d' % (variable, exponent))
            term = '*'.join(factors)
            if not pieces:
                pieces.append(('-' if coefficient < 0 else '') + term)
            else:
                pieces.append(' - ' if coefficient < 0 else ' + ')
                pieces.append(term)
        return (''.join(pieces), ())

    def __eq__(self, other):
        if not isinstance(other, ExactPolynomial):
            return NotImplemented
        return self._terms == other.coefficients()

    def __hash__(self):
        return hash(tuple(sorted(self._terms.items())))

    def __repr__(self):
        return 'ExactPolynomial(%s)' % (self.render()[0],)

    def __str__(self):
        return self.render()[0]
