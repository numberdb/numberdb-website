"""Exact representation of the real numbers NumberDB stores.

Implements `docs/design/number-datastructures.md`. Plain Python -- no Sage, no
Django -- so it runs and is tested on a bare interpreter.

Three layers, deliberately separated:

* **notation** (`Decimal`, `Fraction`) -- what the contributor wrote. Preserved
  rather than derived, because a rendering cannot be recovered from the bounds
  alone: `3.14 +/- 2e-2` denotes [3.12, 3.16], and no decimal expansion is both
  sound and faithful for it -- `3.14` means [3.13, 3.15] and does not contain
  it, while `3.1` means [3.0, 3.2] and is five times wider.
* **semantics** (`Fraction`) -- exact bounds; all comparison and arithmetic.
* **search** (`float`) -- outward-rounded, deliberately lossy, indexed.

`Decimal` is used only for storage and presentation, never for arithmetic,
because its arithmetic is context-rounded (`Decimal(1)/Decimal(3)` gives 28
digits). That is why the notation objects are private to `ExactReal` and the
`Decimal` is never handed out.

`Decimal` rather than `Fraction` for the notation because it preserves
significance, which is load-bearing here: "3.14" and "3.1400" are both 157/50
as rationals, but denote intervals differing by a factor of a hundred.
"""

import math
import re
import sys
from decimal import Decimal, InvalidOperation
from fractions import Fraction

__all__ = [
    'ExactReal',
    'ParseError',
    'parse_real',
]


class ParseError(ValueError):
    """Text is not any documented real-number format."""


# --------------------------------------------------------------------------
# float bounds, rounded outward
# --------------------------------------------------------------------------

def _float_floor(value):
    """Largest float <= value. Never returns something greater."""
    try:
        candidate = float(value)
    except OverflowError:
        # Beyond float range. Below -max it must fall to -inf to stay a lower
        # bound; above +max the largest representable float is still a valid
        # (if useless) lower bound.
        return -math.inf if value < 0 else sys.float_info.max
    if math.isinf(candidate):
        return -math.inf if candidate < 0 else sys.float_info.max
    if Fraction(candidate) > value:
        candidate = math.nextafter(candidate, -math.inf)
    return candidate


def _float_ceil(value):
    """Smallest float >= value. Never returns something smaller."""
    try:
        candidate = float(value)
    except OverflowError:
        return math.inf if value > 0 else -sys.float_info.max
    if math.isinf(candidate):
        return math.inf if candidate > 0 else -sys.float_info.max
    if Fraction(candidate) < value:
        candidate = math.nextafter(candidate, math.inf)
    return candidate


# --------------------------------------------------------------------------
# rendering decimals
# --------------------------------------------------------------------------

def _format_decimal_preserving_significance(value):
    """Render a Decimal so that its precision survives the round trip.

    ``str(Decimal)`` cannot be used: it renders ``Decimal('12e2')`` as
    ``1.2E+3``, and -- worse -- a naive expansion to ``1200`` would be *wrong*.
    Trailing zeros are significant under our convention, so ``1200`` denotes
    [1199, 1201] whereas ``12e2`` denotes [1100, 1300].

    Hence: a non-negative exponent always keeps an explicit ``e``, which also
    keeps ``42e0`` distinguishable from the exact integer ``42`` (a value with
    neither '.' nor 'e' is exact, by definition).
    """
    sign, digits, exponent = value.as_tuple()
    text = ''.join(str(d) for d in digits)
    prefix = '-' if sign else ''

    if exponent >= 0:
        return '%s%se%d' % (prefix, text, exponent)

    point = len(text) + exponent
    if point > 0:
        return '%s%s.%s' % (prefix, text[:point], text[point:])
    return '%s0.%s%s' % (prefix, '0' * (-point), text)


def _format_decimal_exact(value):
    """Render a Decimal that is known exactly.

    Unlike an expansion, no exponent marker is forced: interval endpoints and
    ball components are exact by definition, so there is no expansion/exact
    ambiguity to resolve, and trailing zeros carry no significance. ``2`` reads
    better than ``2e0`` and means the same thing here.
    """
    return format(value, 'f')


def _last_mantissa_digit_index(text):
    """Index of the digit that may be off by one, i.e. the last mantissa digit."""
    mantissa = text.split('e')[0]
    for index in range(len(mantissa) - 1, -1, -1):
        if mantissa[index].isdigit():
            return index
    return None


def _render_exact(value):
    """An exact component: Decimal without a forced exponent, or a Fraction."""
    if isinstance(value, Decimal):
        return _format_decimal_exact(value)
    return str(value)


# --------------------------------------------------------------------------
# notations
# --------------------------------------------------------------------------

class _ExactRational:
    """`5/6`, `-3/2`, `42`. Arbitrary denominator; a degenerate interval."""

    __slots__ = ('value',)

    def __init__(self, value):
        self.value = Fraction(value)

    def bounds(self):
        return (self.value, self.value)

    def render(self):
        return (str(self.value), None)


class _DecimalExpansion:
    """`3.14`, `12e2`. Denotes the value plus or minus one unit in the last place."""

    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value

    def _ulp(self):
        return Fraction(10) ** self.value.as_tuple().exponent

    def bounds(self):
        centre = Fraction(self.value)
        ulp = self._ulp()
        return (centre - ulp, centre + ulp)

    def render(self):
        text = _format_decimal_preserving_significance(self.value)
        return (text, _last_mantissa_digit_index(text))


class _DecimalInterval:
    """`[2, 2.3728596]`. Both endpoints exact; nothing uncertain to mark."""

    __slots__ = ('lower', 'upper')

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def bounds(self):
        return (Fraction(self.lower), Fraction(self.upper))

    def render(self):
        return ('[%s, %s]' % (_render_exact(self.lower),
                              _render_exact(self.upper)), None)


class _DecimalBall:
    """`3.14 +/- 2e-2`. Centre and radius both exact."""

    __slots__ = ('centre', 'radius')

    def __init__(self, centre, radius):
        self.centre = centre
        self.radius = radius

    def bounds(self):
        centre = Fraction(self.centre)
        radius = abs(Fraction(self.radius))
        return (centre - radius, centre + radius)

    def render(self):
        return ('%s +/- %s' % (_render_exact(self.centre),
                               _render_exact(self.radius)), None)


# --------------------------------------------------------------------------
# the wrapper
# --------------------------------------------------------------------------

class ExactReal:
    """The only type callers touch.

    Equality is by *value*, not by spelling: `3.14` and `[3.13, 3.15]` are the
    same set and compare equal. That is deliberate -- dedup and search depend on
    it -- and is the one place where "preserve what was written" and "equal
    things are equal" pull against each other.
    """

    __slots__ = ('_notation',)

    def __init__(self, notation):
        self._notation = notation

    # -- construction -------------------------------------------------------

    @classmethod
    def from_rational(cls, value):
        return cls(_ExactRational(value))

    @classmethod
    def from_expansion(cls, value):
        return cls(_DecimalExpansion(Decimal(value)))

    @classmethod
    def from_interval(cls, lower, upper):
        return cls(_DecimalInterval(lower, upper))

    @classmethod
    def from_ball(cls, centre, radius):
        return cls(_DecimalBall(centre, radius))

    # -- the three layers ---------------------------------------------------

    def bounds(self):
        """Exact bounds as Fractions. Always available, never rounded."""
        return self._notation.bounds()

    def render(self):
        """(text, dotted_index).

        ``dotted_index`` is the position of the digit that may be off by one,
        or None. It is present *exactly* for decimal expansions, so absence of
        a dot means the value is exact -- which is what makes the notation
        self-describing.
        """
        return self._notation.render()

    def search_bounds(self):
        """Outward-rounded float bounds for the index.

        Guaranteed to contain the exact bounds, so the index cannot produce
        false negatives. False positives are expected and are removed by exact
        refinement against ``bounds()``.
        """
        lower, upper = self.bounds()
        return (_float_floor(lower), _float_ceil(upper))

    # -- value semantics ----------------------------------------------------

    def is_exact(self):
        lower, upper = self.bounds()
        return lower == upper

    def width(self):
        lower, upper = self.bounds()
        return upper - lower

    def contains(self, other):
        """True if this interval wholly contains ``other``'s."""
        low, high = self.bounds()
        other_low, other_high = other.bounds()
        return low <= other_low and other_high <= high

    def overlaps(self, other):
        """True if the intervals intersect.

        Necessary for the two entries to denote the same real number, but not
        sufficient -- distinct constants can be indistinguishable at the stored
        precision.
        """
        low, high = self.bounds()
        other_low, other_high = other.bounds()
        return low <= other_high and other_low <= high

    def __eq__(self, other):
        if not isinstance(other, ExactReal):
            return NotImplemented
        return self.bounds() == other.bounds()

    def __hash__(self):
        return hash(self.bounds())

    def __repr__(self):
        return 'ExactReal(%s)' % (self.render()[0],)

    def __str__(self):
        return self.render()[0]


# --------------------------------------------------------------------------
# parsing the documented formats
# --------------------------------------------------------------------------

_RATIONAL = re.compile(r'^([+-]?\d+)/(\d+)$')
_INTEGER = re.compile(r'^[+-]?\d+$')
_DECIMAL = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')
_P_NOTATION = re.compile(r'^([+-]?\d*)[pP]([+-]?\d+)$')
_INTERVAL = re.compile(r'^\[\s*([^,\]]+?)\s*,\s*([^,\]]+?)\s*\]$')
_BALL = re.compile(r'^(.+?)\s*\+/-\s*(.+)$')


def _parse_exact_component(text):
    """An interval endpoint or a ball centre/radius: exact, never uncertain."""
    text = text.strip()
    rational = _RATIONAL.match(text)
    if rational:
        return Fraction(int(rational.group(1)), int(rational.group(2)))
    try:
        return Decimal(text)
    except InvalidOperation:
        raise ParseError('not an exact number: %r' % (text,))


def parse_real(text):
    """Parse any documented real-number format into an ``ExactReal``.

    Formats, from help.html and the front-page search tips:

        42, -3/2         exact integer or rational
        3.14, 12e2       decimal expansion, last digit may be off by one
        1p31415          NumberDB p-notation (normalised to an expansion)
        [2, 2.3728596]   interval, endpoints exact
        3.14 +/- 2e-2    ball, centre and radius exact
    """
    if not isinstance(text, str):
        raise ParseError('expected text')
    text = text.strip()
    if not text:
        raise ParseError('empty')

    interval = _INTERVAL.match(text)
    if interval:
        return ExactReal.from_interval(
            _parse_exact_component(interval.group(1)),
            _parse_exact_component(interval.group(2)))

    ball = _BALL.match(text)
    if ball:
        return ExactReal.from_ball(
            _parse_exact_component(ball.group(1)),
            _parse_exact_component(ball.group(2)))

    rational = _RATIONAL.match(text)
    if rational:
        return ExactReal.from_rational(
            Fraction(int(rational.group(1)), int(rational.group(2))))

    # Before the general decimal rule: a value with neither '.' nor 'e' is an
    # exact integer, not an expansion.
    if _INTEGER.match(text):
        return ExactReal.from_rational(Fraction(int(text)))

    p_notation = _P_NOTATION.match(text)
    if p_notation:
        # "ApB" is defined by translation to the decimal expansion 0.B * 10^A,
        # so it is normalised rather than kept as a notation of its own: it is
        # a shorthand for typing, not a distinct way of writing a number.
        exponent_text, fraction_text = p_notation.groups()
        exponent = int(exponent_text) if exponent_text not in ('', '+', '-') else 0
        negative = fraction_text.startswith('-')
        digits = fraction_text.lstrip('+-')
        mantissa = int(digits)
        if negative:
            mantissa = -mantissa
        return ExactReal.from_expansion(
            Decimal(mantissa).scaleb(exponent - len(digits)))

    if _DECIMAL.match(text):
        return ExactReal.from_expansion(Decimal(text))

    raise ParseError('not a documented real-number format: %r' % (text,))
