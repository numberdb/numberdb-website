"""What gets stored, and how a stored value comes back.

One entry point for the importer and one for readers, so callers do not each
invent their own order of attempts.

Each stored value is two things, per docs/design/number-datastructures.md:

* the **canonical text** -- faithful, what is rendered, the definition of the
  value
* the **search bounds** -- outward-rounded floats, deliberately lossy, indexed

The text is the definition; the bounds are a projection. They must never be
used the other way round: rebuilding a value from its bounds would lose the
notation and, with it, the precision the contributor stated.
"""

from .complex import ExactComplex, parse_complex
from .padic import ExactPAdic, parse_p_adic
from .polynomial import ExactPolynomial, parse_polynomial
from .real import ExactReal, ParseError, parse_real

__all__ = ['KIND_REAL', 'KIND_COMPLEX', 'KIND_P_ADIC', 'KIND_POLYNOMIAL',
           'parse_any', 'canonical_text', 'StoredValue']

KIND_REAL = 'real'
KIND_COMPLEX = 'complex'
KIND_P_ADIC = 'p-adic'
KIND_POLYNOMIAL = 'polynomial'

#: Order matters, because the grammars overlap and the first match wins.
#:
#: * real before polynomial: "1" is both an exact integer and a constant
#:   polynomial, and it should be stored as a number.
#: * complex before polynomial: "1*I" and "i" would otherwise parse as
#:   polynomials in a variable named I.
#: * p-adic before polynomial for the same reason, via its O(p^k) term.
#:
#: Polynomial is last precisely because it is the most permissive: any letter
#: can be a variable, so it would absorb the others given the chance.
_ATTEMPTS = (
    (KIND_REAL, parse_real),
    (KIND_COMPLEX, parse_complex),
    (KIND_P_ADIC, parse_p_adic),
    (KIND_POLYNOMIAL, parse_polynomial),
)

_KINDS = {
    ExactReal: KIND_REAL,
    ExactComplex: KIND_COMPLEX,
    ExactPAdic: KIND_P_ADIC,
    ExactPolynomial: KIND_POLYNOMIAL,
}

_PARSERS = {
    KIND_REAL: parse_real,
    KIND_COMPLEX: parse_complex,
    KIND_P_ADIC: parse_p_adic,
    KIND_POLYNOMIAL: parse_polynomial,
}


class StoredValue:
    """A value as it goes into, and comes out of, the database."""

    __slots__ = ('kind', 'text', 'value')

    def __init__(self, kind, text, value):
        self.kind = kind
        self.text = text
        self.value = value

    def search_bounds(self):
        """Outward-rounded float bounds, or None where the kind has none.

        Reals give (low, high); complex gives (re_low, re_high, im_low,
        im_high). p-adics and polynomials are not ordered, so they are indexed
        by other means -- valuation and prime, and a renaming-invariant key --
        and return None here rather than a meaningless interval.
        """
        if self.kind == KIND_REAL:
            return self.value.search_bounds()
        if self.kind == KIND_COMPLEX:
            return self.value.search_box()
        return None

    def __repr__(self):
        return 'StoredValue(%s, %r)' % (self.kind, self.text)


def parse_any(text):
    """Parse any stored number into a ``StoredValue``.

    Raises ``ParseError`` if no documented format matches, rather than
    guessing: a value nobody can read back is worse than a rejected import.
    """
    if not isinstance(text, str):
        raise ParseError('expected text')
    for kind, parser in _ATTEMPTS:
        try:
            value = parser(text)
        except ParseError:
            continue
        except Exception as error:      # a parser bug, not a rejected input
            raise ParseError('%s parser failed on %r: %s'
                             % (kind, text, error))
        return StoredValue(kind, value.render()[0], value)
    raise ParseError('no documented format matches %r' % (text,))


def canonical_text(text):
    """The canonical spelling of ``text``.

    Canonicalisation is idempotent -- ``canonical_text(canonical_text(x))``
    equals ``canonical_text(x)`` -- which dedup depends on, and which is
    asserted over the whole corpus in tests/test_storage.py.
    """
    return parse_any(text).text


def load(kind, text):
    """Rebuild a value from its stored kind and canonical text."""
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ParseError('unknown kind %r' % (kind,))
    return parser(text)


def kind_of(value):
    """The stored kind of an already-parsed value."""
    try:
        return _KINDS[type(value)]
    except KeyError:
        raise ParseError('not a stored number type: %r' % (type(value),))
