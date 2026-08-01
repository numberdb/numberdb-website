"""Turning what a caller holds into an exact rational.

Every scalar a search function accepts passes through here first, and the
result is always exact. That is the whole point: once endpoints are exact
``Fraction``s, the arithmetic that builds an interval is exact too, so an
interval can never come out narrower than the caller meant. Doing the same
arithmetic in floating point would round, and rounding inward on an endpoint is
a silent false negative -- the number is in the database, and the search does
not find it.

Nothing here is approximate, so there is no rounding direction to get wrong:

* ``int`` is exact.
* ``float`` is a binary fraction, so ``Fraction(0.1)`` is that float's exact
  value. Note this is *not* 1/10 -- ``'0.1'`` and ``0.1`` are different numbers,
  and each converts to itself rather than to the other.
* ``str`` is read as written: ``'1/3'`` and ``'0.1'`` are exact.
* Sage's ``Integer`` and ``Rational`` expose numerator and denominator as
  *methods*, where Python exposes them as attributes. Python's ``Fraction``
  does not raise on a Sage rational -- it stores the bound methods and produces
  nonsense -- so the difference is handled here rather than discovered later.
* Sage's real types answer ``exact_rational()``.

What is refused matters as much. ``numerator``/``denominator`` is an extractor,
never a detector: Sage polynomials and p-adics have both, returning objects of
their own type, so anything that sniffed for them would take a polynomial for a
rational. Every extraction is checked to have produced integers.
"""

from fractions import Fraction
from typing import Any, Protocol, Union, runtime_checkable

__all__ = ['to_exact', 'Scalar', 'SupportsExactRational',
           'SupportsRationalParts', 'SupportsParent']


@runtime_checkable
class SupportsExactRational(Protocol):
    """Sage's reals, which can state themselves as an exact rational."""

    def exact_rational(self) -> Any:
        ...


@runtime_checkable
class SupportsParent(Protocol):
    """Any Sage value: it belongs to a parent, which is what it is classified
    by. Never by its attributes -- Sage polynomials and p-adics both answer
    numerator() with objects of their own type."""

    def parent(self) -> Any:
        ...


@runtime_checkable
class SupportsRationalParts(Protocol):
    """Sage's Integer and Rational, whose parts are methods, not attributes."""

    def numerator(self) -> Any:
        ...

    def denominator(self) -> Any:
        ...


#: What a scalar argument may be.
#:
#: Sage's types are matched structurally rather than by name, because naming
#: them would mean importing Sage and this package must work without it. The
#: protocols are not decoration: writing ``Any`` here instead would collapse
#: the whole union to ``Any``, and a checker would then accept anything at all.
Scalar = Union[int, float, str, Fraction,
               SupportsExactRational, SupportsRationalParts]


def _integer(value: Any, description: str) -> int:
    """An int, or a refusal naming what arrived instead."""
    if isinstance(value, bool):
        raise TypeError('%s is a bool, not a number' % (description,))
    if isinstance(value, int):
        return value
    #Sage's Integer, and anything else that is genuinely integral.
    try:
        converted = int(value)
    except (TypeError, ValueError):
        raise TypeError('%s is %s, which is not an integer'
                        % (description, type(value).__name__))
    if converted != value:
        raise TypeError('%s is not integral' % (description,))
    return converted


def to_exact(value: Scalar, name: str = 'value') -> Fraction:
    """``value`` as an exact ``Fraction``.

    Raises ``TypeError`` for anything that cannot state itself exactly, rather
    than approximating it: a search that quietly used a nearby number would
    return the wrong answer with no sign that it had.
    """
    if isinstance(value, bool):
        raise TypeError('%s is a bool, not a number' % (name,))

    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        #Exact: a float is a binary fraction. Fraction(0.1) is that float's own
        #value, which is not 1/10 -- the caller passed the float, so the float
        #is what is searched for.
        return Fraction(value)
    if isinstance(value, str):
        try:
            return Fraction(value)
        except (TypeError, ValueError):
            raise TypeError('%s is %r, which is not a number' % (name, value))

    #Sage's reals: exact_rational() is the exact value of the stored float,
    #not a rounding of it.
    exact_rational = getattr(value, 'exact_rational', None)
    if callable(exact_rational):
        return to_exact(str(exact_rational()), name)

    #Sage's Integer and Rational. Called if callable, read if not: Python
    #exposes these as attributes and Sage as methods, and Fraction() silently
    #stores the bound methods rather than raising.
    numerator = getattr(value, 'numerator', None)
    denominator = getattr(value, 'denominator', None)
    if numerator is not None and denominator is not None:
        top = numerator() if callable(numerator) else numerator
        bottom = denominator() if callable(denominator) else denominator
        #Checked, because a Sage polynomial's numerator is a polynomial and a
        #p-adic's is a p-adic. Neither is a rational and neither may be taken
        #for one.
        return Fraction(_integer(top, '%s numerator' % (name,)),
                        _integer(bottom, '%s denominator' % (name,)))

    raise TypeError(
        '%s is %s, which cannot be converted exactly. Give an int, a Fraction, '
        'a decimal string, a float, or a Sage number.'
        % (name, type(value).__name__))
