"""Turning NumberDB's JSON into numbers.

This is the security boundary of the package, and a reason it exists at all.
The API used to send a Sage pickle and the example client called ``loads()`` on
it, which runs whatever the bytes say: every user executed code chosen by
whoever answered the request. Here a reply can do exactly one thing -- select a
decoder from the table below and hand it plain JSON. There is no path from a
response to code of the server's choosing.

Values decode to plain Python, so this works in any interpreter; Sage is used
only if the caller asks for a Sage object.

Exact values stay exact. Integers become ``int`` (Python's are unbounded, and
the database holds integers of over a thousand digits) and rationals become
``Fraction``. Interval endpoints arrive as exact ``p/q`` and are kept that way,
so nothing is rounded on the way in -- converting to ``float`` is the caller's
decision, never an accident of transport.

The types here describe *where a number is known to lie*: a real in an
interval, a complex value in a rectangle, a p-adic in a ball. They are records,
not arithmetic types. They deliberately do not add, multiply or track
precision -- that is what ``.sage()`` is for. This is why ``ComplexInterval``
can share a name with Sage's notion without pretending to be it: the region is
the same shape, the behaviour is not.
"""

import math
from fractions import Fraction
from typing import Any, Dict, FrozenSet, Optional, Union

from ._convert import Scalar, to_exact
from ._errors import UnsupportedNumber

__all__ = ['decode', 'to_sage', 'KINDS', 'RealInterval', 'ComplexInterval',
           'PAdic', 'Polynomial']


class RealInterval:
    """A real number known to lie between two exact rationals.

    Endpoints are ``Fraction``, or ``float`` infinities where the database
    holds a value too large for a float to bound. A record, not an arithmetic
    type: use ``.sage()`` on the result to compute with it.
    """

    __slots__ = ('lower', 'upper')

    def __init__(self, lower: Scalar, upper: Scalar) -> None:
        #Converted here, not merely annotated. The type checker found this:
        #the signature promised a Scalar and the class assumed a Fraction, so
        #RealInterval('1/3', '1/2') held strings and broke on arithmetic.
        self.lower = _endpoint(lower)
        self.upper = _endpoint(upper)

    def __repr__(self):
        if self.lower == self.upper:
            return 'RealInterval(%s)' % (self.lower,)
        return 'RealInterval(%s, %s)' % (self.lower, self.upper)

    def __eq__(self, other):
        return (isinstance(other, RealInterval) and self.lower == other.lower
                and self.upper == other.upper)

    #Defining __eq__ removes the inherited __hash__, which would make these
    #unusable in a set or as a dict key -- a natural thing to want to do with
    #numbers.
    def __hash__(self):
        return hash((RealInterval, self.lower, self.upper))

    def __float__(self):
        """The midpoint. Lossy by definition, which is why it is explicit."""
        return float(self.midpoint())

    def midpoint(self) -> Union[Fraction, float]:
        """Undefined for an unbounded interval, where it is an infinity."""
        return self.lower + (self.upper - self.lower) / 2

    @property
    def is_exact(self) -> bool:
        """True when the interval is a single point, so nothing is unknown."""
        return self.lower == self.upper


class ComplexInterval:
    """A complex number known to lie in a rectangle.

    ``real`` and ``imag`` are each a ``RealInterval``. Named as Python's own
    ``complex`` names them, and as Sage does, so the abbreviation is the one
    already in the reader's fingers.

    The same shape as Sage's complex interval -- a real interval for each
    component -- but a record rather than an arithmetic type, with exact
    rational corners instead of floats at a fixed precision.
    """

    __slots__ = ('real', 'imag')

    def __init__(self, real: 'RealInterval', imag: 'RealInterval') -> None:
        self.real = real
        self.imag = imag

    def __repr__(self):
        return 'ComplexInterval(%r, %r)' % (self.real, self.imag)

    def __eq__(self, other):
        return (isinstance(other, ComplexInterval) and self.real == other.real
                and self.imag == other.imag)

    def __hash__(self):
        return hash((ComplexInterval, self.real, self.imag))

    def __complex__(self):
        """The centre. Lossy, as for a real interval."""
        return complex(float(self.real), float(self.imag))

    @property
    def is_exact(self) -> bool:
        return self.real.is_exact and self.imag.is_exact


class PAdic:
    """A p-adic number, as the ball ``prime**valuation * unit + O(prime**k)``.

    Normalised, which is what makes equality mean anything: ``unit`` is coprime
    to ``prime`` and reduced modulo ``prime**precision_relative``, so a ball has
    exactly one representation. A bare representative would not -- 1 and
    1 + p**k denote the same ball at precision k, and would have compared
    unequal and hashed apart.

    ``valuation`` is the order, and is negative off Z_p: 1/5 in Q_5 has
    valuation -1. A thousand of the p-adics in the database do.

    Both precisions are named, never a bare ``precision``. They coincide at
    valuation zero and diverge silently elsewhere::

        precision_absolute = valuation + precision_relative

        6 in Q_5     valuation  0   relative 20   absolute 20
        1/5 in Q_5   valuation -1   relative 20   absolute 19
        25 in Q_5    valuation  2   relative 20   absolute 22

    ``O(p^k)`` in the string form is the absolute one.

    Zero has no order and no unit: it is written with ``unit`` zero and
    ``valuation`` equal to the absolute precision, the ball about zero.
    """

    __slots__ = ('prime', 'valuation', 'unit', 'precision_absolute')

    def __init__(self, prime: int, valuation: int, unit: int,
                 precision_absolute: int) -> None:
        prime = int(prime)
        unit = int(unit)
        relative = int(precision_absolute) - int(valuation)
        if unit and relative > 0:
            if unit % prime == 0:
                raise ValueError(
                    'unit %d is divisible by %d; a p-adic is normalised as '
                    'prime**valuation * unit with the unit coprime to the '
                    'prime' % (unit, prime))
            #Reduced so that one ball has one representation.
            unit %= prime ** relative
        self.prime = prime
        self.valuation = int(valuation)
        self.unit = unit
        self.precision_absolute = int(precision_absolute)

    @property
    def precision_relative(self) -> int:
        """Digits of the unit that are known."""
        return self.precision_absolute - self.valuation

    @property
    def value(self) -> Fraction:
        """The representative ``prime**valuation * unit``, as a Fraction."""
        return Fraction(self.prime) ** self.valuation * Fraction(self.unit)

    def __repr__(self):
        return 'PAdic(%d, %d, %d, %d)' % (self.prime, self.valuation,
                                          self.unit, self.precision_absolute)

    def __str__(self):
        return '%s + O(%d^%d)' % (self.value, self.prime,
                                  self.precision_absolute)

    def __eq__(self, other):
        return (isinstance(other, PAdic) and self.prime == other.prime
                and self.valuation == other.valuation
                and self.unit == other.unit
                and self.precision_absolute == other.precision_absolute)

    def __hash__(self):
        return hash((PAdic, self.prime, self.valuation, self.unit,
                     self.precision_absolute))


class Polynomial:
    """A polynomial over the rationals, as the database writes it.

    Exact, so there is no region: ``text`` is the polynomial itself.
    """

    __slots__ = ('variable_count', 'text')

    def __init__(self, variable_count: int, text: str) -> None:
        self.variable_count = variable_count
        self.text = text

    def __repr__(self):
        return 'Polynomial(%r)' % (self.text,)

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return isinstance(other, Polynomial) and self.text == other.text

    def __hash__(self):
        return hash((Polynomial, self.text))


def _endpoint(value: Scalar) -> Union[Fraction, float]:
    """An endpoint as an exact rational, or an infinity.

    Infinities are the one thing a Fraction cannot hold, and the database has
    them: values past what a float can bound arrive with one end unbounded.
    """
    if isinstance(value, float) and math.isinf(value):
        return value
    return to_exact(value, 'endpoint')


def _rational(text):
    """An endpoint, sent as exact ``p/q`` and kept exact."""
    text = str(text)
    try:
        return Fraction(text)
    except (TypeError, ValueError):
        #Infinities and decimal fallbacks. Fraction cannot hold an infinity, so
        #the float stands in; it is still an outward bound.
        return float(text)


def _decode_real_interval(record):
    return RealInterval(_rational(record['lower']), _rational(record['upper']))


def _decode_complex_interval(record):
    return ComplexInterval(
        RealInterval(_rational(record['re_lower']),
                     _rational(record['re_upper'])),
        RealInterval(_rational(record['im_lower']),
                     _rational(record['im_upper'])))


def _decode_integer(record):
    return int(record['value'])


def _decode_rational(record):
    return Fraction(record['value'])


def _decode_p_adic(record):
    return PAdic(int(record['prime']), int(record['valuation']),
                 int(record['unit']), int(record['precision']))


def _decode_polynomial(record):
    return Polynomial(int(record['variables']), str(record['value']))


#: Fixed table. Dispatch never resolves a name taken from the response, so a
#: reply can only ever produce one of these types.
#:
#: Kinds are the server's vocabulary and are expected to grow. An unrecognised
#: one is refused individually, never fatally -- see ``Result.value``.
_DECODERS = {
    'ZZ': _decode_integer,
    'QQ': _decode_rational,
    'RIF': _decode_real_interval,
    'RBF': _decode_real_interval,
    'CIF': _decode_complex_interval,
    'Qp': _decode_p_adic,
    'polynomial': _decode_polynomial,
}

#: What this version can read. Exposed so a caller can check before relying on
#: a kind, rather than discovering it through an exception.
KINDS = frozenset(_DECODERS)


def decode(record: Dict[str, Any]) -> Any:
    """A number from its JSON record."""
    if not isinstance(record, dict):
        raise UnsupportedNumber('number record must be an object, got %s'
                                % (type(record).__name__,))
    kind = record.get('kind')
    decoder = _DECODERS.get(kind) if isinstance(kind, str) else None
    if decoder is None:
        raise UnsupportedNumber(
            'this version of numberdb cannot read %r; the server may be newer '
            'than the package -- try upgrading it' % (kind,))
    try:
        return decoder(record)
    except (KeyError, TypeError, ValueError) as error:
        raise UnsupportedNumber('malformed %s record: %s' % (kind, error))


def _sage_rings():
    """Sage's number types, however this installation spells them.

    Two import paths because there are two Sages. Full SageMath has the
    monolithic ``sage.rings.all``; passagemath, the distribution split into pip
    packages, does not -- there each name lives in its own module.

    ``sage.rings.all`` is tried first, and the order matters. In full SageMath,
    importing ``sage.rings.integer_ring`` before anything else has initialised
    Sage raises "partially initialized module ... most likely due to a circular
    import". Going through the package's own aggregate module avoids that,
    and where it does not exist the ModuleNotFoundError is clean and the
    specific modules work.
    """
    try:
        from sage.rings.all import ZZ, QQ, RIF, CIF, Qp, PolynomialRing
        return ZZ, QQ, RIF, CIF, Qp, PolynomialRing
    except ImportError:
        pass
    try:
        from sage.rings.integer_ring import ZZ
        from sage.rings.rational_field import QQ
        from sage.rings.real_mpfi import RIF
        from sage.rings.cif import CIF
        from sage.rings.padics.factory import Qp
        from sage.rings.polynomial.polynomial_ring_constructor import \
            PolynomialRing
        return ZZ, QQ, RIF, CIF, Qp, PolynomialRing
    except ImportError:
        raise ImportError(
            'SageMath is required to convert a NumberDB result to a Sage '
            'object. The value itself is available without Sage: see '
            '.value and .exact_text')


def to_sage(value: Any) -> Any:
    """The same number as a Sage object.

    Kept apart from decoding so the package works without Sage. Importing Sage
    costs seconds, and most uses -- looking a number up, reading its exact
    form -- never need it.
    """
    ZZ, QQ, RIF, CIF, Qp, PolynomialRing = _sage_rings()

    def endpoint(bound: Any) -> Any:
        """An endpoint as Sage wants it, infinities included.

        The database holds values past what a float can bound -- an
        integer of 400 digits, say -- and the server sends that end as
        '-infinity'. QQ has no such element and raises on one, so the float is
        passed through: RIF accepts it and yields a genuinely unbounded
        interval, which is what the value means.
        """
        if isinstance(bound, float) and math.isinf(bound):
            return bound
        return QQ(bound)

    def interval(real_interval: 'RealInterval') -> Any:
        return RIF(endpoint(real_interval.lower), endpoint(real_interval.upper))

    if isinstance(value, RealInterval):
        return interval(value)
    if isinstance(value, ComplexInterval):
        return CIF(interval(value.real), interval(value.imag))
    if isinstance(value, PAdic):
        field = Qp(value.prime,
                   prec=max(abs(value.precision_absolute)
                            + abs(value.valuation) + 1, 1))
        #add_bigoh sets absolute precision, which is what the type carries;
        #Qp's own prec is a relative cap and would not reproduce it.
        return field(QQ(value.prime) ** value.valuation
                     * QQ(value.unit)).add_bigoh(value.precision_absolute)
    if isinstance(value, Polynomial):
        return PolynomialRing(QQ, max(value.variable_count, 1),
                              'x')(value.text)
    if isinstance(value, bool):
        #bool is an int subclass; reaching ZZ(True) would be a silent absurdity.
        raise UnsupportedNumber('no Sage form for a boolean')
    if isinstance(value, int):
        return ZZ(value)
    if isinstance(value, Fraction):
        return QQ(value.numerator) / QQ(value.denominator)
    raise UnsupportedNumber('no Sage form for %s' % (type(value).__name__,))
