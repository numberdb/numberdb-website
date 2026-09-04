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
from ._errors import UnsupportedNumberError

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
        """True when the interval is a single point, so nothing is unknown.

        The value is known exactly; the *representation* is still an interval.
        A zero-width interval is not a rational, and asking this must not be
        read as permission to treat it as one.
        """
        return self.lower == self.upper


def _as_part(value):
    """One component of a complex value: exact, or an interval.

    A pair of *existing* types, which is what the database stores: a rational
    for a component given exactly, a ``RealInterval`` for one given as a
    range. Nothing new is invented.

    Two different questions live near this word, and they must not be run
    together:

    * **Is the value known exactly?** A property of the number. A
      ``RealInterval`` whose endpoints agree pins the value to a point, so the
      answer is *yes*, and ``is_exact`` says so. Interval arithmetic that
      lands on a point has proved the value.
    * **Is this an exact type?** A property of the representation, which is
      what this function decides. A zero-width interval is *not* an exact
      type; it is an interval that happens to be narrow.

    The second question has teeth only where the rational is not dyadic.
    ``Fraction(1, 13)`` is written ``1/13``; no binary interval can ever pin
    1/13 to zero width, so an interval there is a decimal however hard it
    tries. Where the value *is* dyadic the two coincide on the page, and
    should: both assert the same number.

    What is never done is the reverse -- reading a measured width as a
    declaration. Wrapping a fixed-precision result in an interval field gives
    width zero without any interval arithmetic having happened, which is how
    twenty-nine tables came to promise digits nobody had proved; the
    ``proven`` check refuses such a value rather than believing it.
    """
    from fractions import Fraction

    if isinstance(value, RealInterval):
        return value
    if isinstance(value, bool):
        raise TypeError('a boolean is not a number')
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    raise TypeError(
        'a component of a complex number is an exact rational -- int or '
        'Fraction -- or a RealInterval. Got %s. A Sage interval or ball can '
        'be given as the whole value instead, or converted with '
        'RealInterval(lower, upper).' % (type(value).__name__,))


def _part_bounds(part):
    """A component's endpoints, as exact Fractions."""
    from fractions import Fraction

    if isinstance(part, RealInterval):
        return part.lower, part.upper
    return Fraction(part), Fraction(part)


class ComplexInterval:
    """A complex number, as a pair of components.

    ``real`` and ``imag`` are each either an exact rational -- ``int`` or
    ``Fraction`` -- or a ``RealInterval``. Named as Python's own ``complex``
    names them, and as Sage does, so the abbreviation is the one already in
    the reader's fingers.

    The pair is what lets the two halves differ in what is known about them.
    ``ComplexInterval(Fraction(-1, 2), RealInterval(lo, hi))`` is written
    ``-1/2 + i * 0.86602540378?``: exact on one axis and an approximation on
    the other, which is what a Jacobi sum or a quadratic algebraic number
    actually is. Forcing both through one interval wrote the real part of
    (3 + i*sqrt(3))/2 as ninety-nine digits of 1.5, in the one notation --
    a decimal expansion -- that cannot say a value is exact, because it means
    plus or minus one unit in the last place however many digits it carries.

    A record rather than an arithmetic type, with exact rational corners
    instead of floats at a fixed precision.
    """

    __slots__ = ('real', 'imag')

    def __init__(self, real, imag) -> None:
        self.real = _as_part(real)
        self.imag = _as_part(imag)

    def bounds(self):
        """``((re_low, re_high), (im_low, im_high))`` as exact Fractions."""
        return _part_bounds(self.real), _part_bounds(self.imag)

    def __repr__(self):
        return 'ComplexInterval(%r, %r)' % (self.real, self.imag)

    def __eq__(self, other):
        return (isinstance(other, ComplexInterval) and self.real == other.real
                and self.imag == other.imag)

    def __hash__(self):
        return hash((ComplexInterval, self.real, self.imag))

    def __complex__(self):
        """The centre. Lossy, as for a real interval."""
        (re_low, re_high), (im_low, im_high) = self.bounds()
        return complex(float(re_low + (re_high - re_low) / 2),
                       float(im_low + (im_high - im_low) / 2))

    @property
    def is_exact(self) -> bool:
        """True when the value is known exactly: the box is a single point.

        A statement about the number, not about how it is written. A
        component given as a ``RealInterval`` whose endpoints agree is exact
        in this sense and is still not an exact *type* -- which is a separate
        question, answered by ``isinstance(part, Fraction)``, and the one that
        decides whether it is written ``1/13`` or as a decimal.
        """
        (re_low, re_high), (im_low, im_high) = self.bounds()
        return re_low == re_high and im_low == im_high


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
        raise UnsupportedNumberError('number record must be an object, got %s'
                                % (type(record).__name__,))
    kind = record.get('kind')
    decoder = _DECODERS.get(kind) if isinstance(kind, str) else None
    if decoder is None:
        raise UnsupportedNumberError(
            'this version of numberdb cannot read %r; the server may be newer '
            'than the package -- try upgrading it' % (kind,))
    try:
        return decoder(record)
    except (KeyError, TypeError, ValueError) as error:
        raise UnsupportedNumberError('malformed %s record: %s' % (kind, error))


class _MissingRing:
    """Stands in for a ring this installation does not have.

    passagemath is modular: `pip install passagemath-symbolics` gives real and
    complex intervals and polynomials and no p-adics at all. Importing the six
    rings together meant a missing one broke conversion of every kind --
    a real number could not be converted because p-adics were not installed,
    which is nobody's idea of a dependency.

    So each ring is fetched on its own and a missing one becomes this, which
    says what to install at the point where something actually needs it.
    """

    def __init__(self, name, distribution):
        self._name = name
        self._distribution = distribution

    def __call__(self, *args, **kwargs):
        raise ImportError(
            'converting this value needs %s, which this SageMath does not '
            'have. With passagemath: `pip install %s`.'
            % (self._name, self._distribution))

    def __repr__(self):
        return '<%s missing: pip install %s>' % (self._name,
                                                 self._distribution)


def _prime_sage():
    """Make it safe to import Sage's ring modules directly.

    Importing `sage.rings.integer_ring` before anything has initialised Sage
    raises "partially initialized module ... most likely due to a circular
    import" -- on full SageMath, and on passagemath, where it is the first
    thing that happens because there is no `sage.rings.all` to go through.
    Importing `sage.rings.integer` first does the initialisation, after which
    the rest import cleanly. Measured on passagemath-symbolics 10.8.9.
    """
    try:
        import sage.rings.integer            # noqa: F401  (imported for effect)
    except ImportError:
        pass


def _sage_rings():
    """Sage's number types, however this installation spells them.

    Two import paths because there are two Sages. Full SageMath has the
    monolithic ``sage.rings.all``; passagemath, the distribution split into pip
    packages, does not -- there each name lives in its own module, and which
    modules exist depends on which distributions are installed.

    A ring that is absent comes back as `_MissingRing`, which raises only if
    something asks for it. That is the difference between "this installation
    cannot do p-adics" and "this installation cannot do anything".
    """
    try:
        from sage.rings.all import ZZ, QQ, RIF, CIF, Qp, PolynomialRing
        return ZZ, QQ, RIF, CIF, Qp, PolynomialRing
    except ImportError:
        pass

    _prime_sage()

    #Which passagemath distribution ships which ring, read out of the wheels
    #rather than guessed: three of these were guessed first and three were
    #wrong. An error message that names the wrong package to install is worse
    #than one that names none.
    wanted = (
        ('ZZ', 'sage.rings.integer_ring', 'ZZ',
         'integers', 'passagemath-categories'),
        ('QQ', 'sage.rings.rational_field', 'QQ',
         'rationals', 'passagemath-categories'),
        ('RIF', 'sage.rings.real_mpfi', 'RIF',
         'real intervals', 'passagemath-flint'),
        ('CIF', 'sage.rings.cif', 'CIF',
         'complex intervals', 'passagemath-flint'),
        ('Qp', 'sage.rings.padics.factory', 'Qp',
         'p-adic numbers', 'passagemath-pari'),
        ('PolynomialRing', 'sage.rings.polynomial.polynomial_ring_constructor',
         'PolynomialRing', 'polynomials', 'passagemath-categories'),
    )

    found = []
    for _, module_name, attribute, description, distribution in wanted:
        try:
            module = __import__(module_name, fromlist=[attribute])
            found.append(getattr(module, attribute))
        except (ImportError, AttributeError):
            found.append(_MissingRing(description, distribution))

    if all(isinstance(ring, _MissingRing) for ring in found):
        raise ImportError(
            'SageMath is required to convert a NumberDB result to a Sage '
            'object. The value itself is available without Sage: see '
            '.value and .exact_text')
    return tuple(found)


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
        #Named as the text names them. A ring of x0, x1, ... cannot accept
        #"x^2+y": Sage reports that it cannot map the element into the ring,
        #which made every multivariate polynomial undecodable.
        from ._polynomial import parse_polynomial
        names = parse_polynomial(value.text).variables() or ['x']
        return PolynomialRing(QQ, len(names), names)(value.text)
    if isinstance(value, bool):
        #bool is an int subclass; reaching ZZ(True) would be a silent absurdity.
        raise UnsupportedNumberError('no Sage form for a boolean')
    if isinstance(value, int):
        return ZZ(value)
    if isinstance(value, Fraction):
        return QQ(value.numerator) / QQ(value.denominator)
    raise UnsupportedNumberError('no Sage form for %s' % (type(value).__name__,))
