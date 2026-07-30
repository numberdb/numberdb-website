"""Conversion between the exact number layer and Sage.

Deliberately **not** imported by ``utils/numbers/__init__.py``. Importing
``utils.numbers`` must not pull SageMath in, because the point of the exact
layer is that the web container stops carrying a computer algebra system beside
its database credentials -- ~187 MB of RSS and 3.7 s of import per gunicorn
worker on a 1 GB machine, for arithmetic it does not do.

Only two callers need this module:

* the **evaluator**, which produces Sage values from user search programs and
  must turn them into ``ExactReal`` / ``ExactComplex``
* the **importer**, where a Sage value arrives from a ``generate.sage`` script

Note the import path does *not* need it for ordinary data: numbers in
``numberdb-data`` are text in the documented formats, so ``parse_real`` reads
them directly and exactly, with no Sage and no binary rounding on the way in.

Direction matters for soundness:

* **to Sage** is lossy but must stay *sound* -- the returned interval always
  contains the exact one, so nothing is silently narrowed.
* **from Sage** is exact -- a Sage interval has dyadic endpoints, which are
  rationals, so no precision is lost coming back.
"""

from fractions import Fraction

from sage.rings.all import QQ, RealIntervalField, ComplexIntervalField
from sage.rings.all import RealBallField

from .complex import ExactComplex
from .real import ExactReal

__all__ = [
    'to_real_interval',
    'to_real_ball',
    'to_complex_interval',
    'from_real_interval',
    'from_complex_interval',
]

#: Enough for the documented formats to survive a round trip in practice;
#: callers wanting more can pass their own precision.
DEFAULT_PRECISION = 1000


def _rational_to_sage(value):
    """Fraction -> Sage rational, exactly."""
    return QQ(int(value.numerator)) / QQ(int(value.denominator))


def to_real_interval(value, precision=DEFAULT_PRECISION):
    """``ExactReal`` -> Sage ``RealIntervalFieldElement``.

    Lossy -- binary cannot represent 313/100 -- but sound: the result contains
    the exact interval, because ``RIF(a, b)`` rounds its endpoints outward.
    """
    field = RealIntervalField(precision)
    lower, upper = value.bounds()
    return field(_rational_to_sage(lower), _rational_to_sage(upper))


def to_real_ball(value, precision=DEFAULT_PRECISION):
    """``ExactReal`` -> Sage ``RealBall``, via the interval so it stays sound."""
    return RealBallField(precision)(to_real_interval(value, precision))


def to_complex_interval(value, precision=DEFAULT_PRECISION):
    """``ExactComplex`` -> Sage ``ComplexIntervalFieldElement``."""
    field = ComplexIntervalField(precision)
    return field(to_real_interval(value.real(), precision),
                 to_real_interval(value.imag(), precision))


def _endpoint_to_fraction(endpoint):
    """A Sage real endpoint -> Fraction, exactly.

    Interval endpoints are dyadic rationals, so this loses nothing.
    """
    try:
        exact = endpoint.exact_rational()
        return Fraction(int(exact.numerator()), int(exact.denominator()))
    except (AttributeError, TypeError, ValueError):
        # Infinities and anything without an exact rational have no place in a
        # stored value; refuse rather than invent one.
        raise ValueError('cannot represent %r exactly' % (endpoint,))


def from_real_interval(element):
    """Sage real interval or ball -> ``ExactReal``.

    Produces an interval notation with rational endpoints. The result is not a
    decimal expansion even when the input came from one: the binary endpoints
    are generally not decimal, and inventing an expansion would claim a
    precision boundary the value does not have.
    """
    try:
        lower = element.lower()
        upper = element.upper()
    except AttributeError:
        # A real ball exposes the same information differently.
        interval = RealIntervalField(element.parent().precision())(element)
        lower, upper = interval.lower(), interval.upper()
    return ExactReal.from_interval(_endpoint_to_fraction(lower),
                                   _endpoint_to_fraction(upper))


def from_complex_interval(element):
    """Sage complex interval or ball -> ``ExactComplex``."""
    return ExactComplex(from_real_interval(element.real()),
                        from_real_interval(element.imag()))
