"""Turning NumberDB's JSON into numbers.

This is the security boundary of the package, and the reason the package exists
at all. The API used to send a Sage pickle and the example client called
``loads()`` on it, which runs whatever the bytes say: every user executed code
chosen by whoever answered the request. Here a reply can do exactly one thing --
select a decoder from the table below and hand it plain JSON. There is no path
from a response to code of the server's choosing.

Values are decoded to plain Python, so this works in any interpreter. Sage is
used only if the caller asks for a Sage object.

Exact values stay exact. Integers become ``int`` (Python's are unbounded, and
the database holds integers of over a thousand digits) and rationals become
``Fraction``. Interval endpoints are sent as exact ``p/q`` and are kept that
way, so nothing is rounded on the way in; converting to ``float`` is the
caller's decision, not an accident of transport.
"""

from fractions import Fraction

__all__ = ['decode', 'Interval', 'Box', 'PAdic', 'Polynomial',
           'UnsupportedNumber']


class UnsupportedNumber(Exception):
    """A number this version of the package has no rule for.

    Usually means the server is newer than the package; upgrading is the fix.
    Raised rather than guessed at, because a wrong guess about a number is
    worse than no answer.
    """


class Interval:
    """A real known to lie between two exact rationals."""

    __slots__ = ('lower', 'upper')

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper

    def __repr__(self):
        if self.lower == self.upper:
            return 'Interval(%s)' % (self.lower,)
        return 'Interval(%s, %s)' % (self.lower, self.upper)

    def __eq__(self, other):
        return (isinstance(other, Interval) and self.lower == other.lower
                and self.upper == other.upper)

    def __float__(self):
        """The midpoint. Lossy by definition, hence explicit."""
        return float(self.lower + (self.upper - self.lower) / 2)

    @property
    def is_exact(self):
        return self.lower == self.upper


class Box:
    """A complex number known to lie in a rectangle."""

    __slots__ = ('real', 'imaginary')

    def __init__(self, real, imaginary):
        self.real = real
        self.imaginary = imaginary

    def __repr__(self):
        return 'Box(%r, %r)' % (self.real, self.imaginary)

    def __eq__(self, other):
        return (isinstance(other, Box) and self.real == other.real
                and self.imaginary == other.imaginary)

    def __complex__(self):
        return complex(float(self.real), float(self.imaginary))


class PAdic:
    """``lift + O(prime**precision)``."""

    __slots__ = ('prime', 'precision', 'lift')

    def __init__(self, prime, precision, lift):
        self.prime = prime
        self.precision = precision
        self.lift = lift

    def __repr__(self):
        return 'PAdic(%d, %d, %d)' % (self.prime, self.precision, self.lift)

    def __eq__(self, other):
        return (isinstance(other, PAdic) and self.prime == other.prime
                and self.precision == other.precision
                and self.lift == other.lift)


class Polynomial:
    """A polynomial over the rationals, as written."""

    __slots__ = ('variables', 'text')

    def __init__(self, variables, text):
        self.variables = variables
        self.text = text

    def __repr__(self):
        return 'Polynomial(%r)' % (self.text,)

    def __eq__(self, other):
        return isinstance(other, Polynomial) and self.text == other.text


def _rational(text):
    """An endpoint, sent as exact ``p/q`` and kept exact."""
    text = str(text)
    try:
        return Fraction(text)
    except (TypeError, ValueError):
        # Infinities and decimal fallbacks. Fraction cannot hold an infinity,
        # so the float stands in; it is still an outward bound.
        return float(text)


def _decode_interval(record):
    return Interval(_rational(record['lower']), _rational(record['upper']))


def _decode_box(record):
    return Box(Interval(_rational(record['re_lower']),
                        _rational(record['re_upper'])),
               Interval(_rational(record['im_lower']),
                        _rational(record['im_upper'])))


def _decode_integer(record):
    return int(record['value'])


def _decode_rational(record):
    return Fraction(record['value'])


def _decode_p_adic(record):
    return PAdic(int(record['prime']), int(record['precision']),
                 int(record['lift']))


def _decode_polynomial(record):
    return Polynomial(int(record['variables']), str(record['value']))


#: Fixed table. Dispatch never resolves a name taken from the response, so a
#: reply can only ever produce one of these types.
_DECODERS = {
    'ZZ': _decode_integer,
    'QQ': _decode_rational,
    'RIF': _decode_interval,
    'RBF': _decode_interval,
    'CIF': _decode_box,
    'Qp': _decode_p_adic,
    'polynomial': _decode_polynomial,
}

#: What this package can read. Exposed so a caller can check before relying on
#: a kind, rather than discovering it through an exception.
KINDS = frozenset(_DECODERS)


def decode(record):
    """A number from its JSON record."""
    if not isinstance(record, dict):
        raise UnsupportedNumber('number record must be an object, got %s'
                                % (type(record).__name__,))
    kind = record.get('kind')
    decoder = _DECODERS.get(kind)
    if decoder is None:
        raise UnsupportedNumber(
            'this version of numberdb cannot read %r; the server may be newer '
            'than the package -- try upgrading it' % (kind,))
    try:
        return decoder(record)
    except (KeyError, TypeError, ValueError) as error:
        raise UnsupportedNumber('malformed %s record: %s' % (kind, error))


def to_sage(value):
    """The same number as a Sage object.

    Kept apart from decoding so the package works without Sage. Importing Sage
    costs seconds and most uses -- looking a number up, reading its exact
    form -- never need it.
    """
    try:
        from sage.rings.all import ZZ, QQ, RIF, CIF, Qp, PolynomialRing
    except ImportError:
        raise ImportError(
            'SageMath is required to convert a NumberDB result to a Sage '
            'object. The value itself is available without Sage: see '
            '.value and .exact_text')

    if isinstance(value, Interval):
        return RIF(QQ(value.lower), QQ(value.upper))
    if isinstance(value, Box):
        return CIF(RIF(QQ(value.real.lower), QQ(value.real.upper)),
                   RIF(QQ(value.imaginary.lower), QQ(value.imaginary.upper)))
    if isinstance(value, PAdic):
        return Qp(value.prime, prec=max(value.precision, 1))(ZZ(value.lift))
    if isinstance(value, Polynomial):
        return PolynomialRing(QQ, max(value.variables, 1), 'x')(value.text)
    if isinstance(value, int):
        return ZZ(value)
    if isinstance(value, Fraction):
        return QQ(value.numerator) / QQ(value.denominator)
    raise UnsupportedNumber('no Sage form for %r' % (type(value).__name__,))
