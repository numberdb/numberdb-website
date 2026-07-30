"""Exact representation of the complex numbers NumberDB stores.

A complex value is a pair of `ExactReal` -- a box with exact corners, matching
the front-page grammar: "sums or differences of the form A or i*A or A*i, where
A is a real number in the above format or a rational number".

Being a pair is what makes mixed exactness fall out for free. `5/6 + 5.5I`
holds an exact rational on one axis and a decimal expansion on the other, which
the four-float schema could not express at all: it stored `5/6` as
[0.833333333333333, 0.833333333333334] and lost the exactness at import.
"""

from .real import ExactReal, ParseError, parse_real

__all__ = ['ExactComplex', 'parse_complex']


class ExactComplex:
    """A complex value as a pair of `ExactReal`.

    Equality is by value, as for reals, so two spellings of the same box
    compare equal.
    """

    __slots__ = ('_real', '_imaginary')

    def __init__(self, real, imaginary):
        if not isinstance(real, ExactReal) or not isinstance(imaginary, ExactReal):
            raise TypeError('components must be ExactReal')
        self._real = real
        self._imaginary = imaginary

    def real(self):
        return self._real

    def imag(self):
        return self._imaginary

    def bounds(self):
        """((re_low, re_high), (im_low, im_high)) as exact Fractions."""
        return (self._real.bounds(), self._imaginary.bounds())

    def search_box(self):
        """(re_low, re_high, im_low, im_high) as outward-rounded floats.

        The rectangle to hand a spatial index. Guaranteed to contain the exact
        box, so the index cannot produce false negatives.
        """
        re_low, re_high = self._real.search_bounds()
        im_low, im_high = self._imaginary.search_bounds()
        return (re_low, re_high, im_low, im_high)

    def render(self):
        """(text, dotted_indices) in the documented "A + B*I" form.

        A wholly negative imaginary part folds into the joining sign, so
        results read `a - b*I` rather than `a + -b*I`. That needs exact
        negation rather than string surgery: an interval component renders as
        `[-0.3, -0.1]`, which does not begin with a sign that could be moved.

        Both components can be uncertain, which is why indices are a tuple.
        """
        real_text, real_dots = self._real.render()

        imaginary = self._imaginary
        if imaginary.bounds()[1] < 0:
            joiner = ' - '
            imaginary = -imaginary
        else:
            joiner = ' + '
        imaginary_text, imaginary_dots = imaginary.render()

        text = '%s%s%s*I' % (real_text, joiner, imaginary_text)
        offset = len(real_text) + len(joiner)
        dots = tuple(real_dots) + tuple(i + offset for i in imaginary_dots)
        return (text, dots)

    def is_exact(self):
        return self._real.is_exact() and self._imaginary.is_exact()

    def overlaps(self, other):
        """True if the boxes intersect.

        Necessary for the two entries to denote the same complex number, but
        not sufficient: distinct constants can be indistinguishable at the
        stored precision.
        """
        return (self._real.overlaps(other.real())
                and self._imaginary.overlaps(other.imag()))

    def contains(self, other):
        return (self._real.contains(other.real())
                and self._imaginary.contains(other.imag()))

    def __eq__(self, other):
        if not isinstance(other, ExactComplex):
            return NotImplemented
        return self.bounds() == other.bounds()

    def __hash__(self):
        return hash(self.bounds())

    def __repr__(self):
        return 'ExactComplex(%s)' % (self.render()[0],)

    def __str__(self):
        return self.render()[0]


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def _split_terms(text):
    """Split into (sign, term) at top-level '+'/'-'.

    Separators inside brackets are ignored, so a component may itself be an
    interval. Requiring a digit, ')' or ']' before the sign is what keeps the
    '-' in `1e-5` attached to its exponent rather than splitting there.
    """
    terms = []
    depth = 0
    start = 0
    sign = 1
    for index, character in enumerate(text):
        if character in '[(':
            depth += 1
        elif character in '])':
            depth -= 1
        elif (character in '+-' and depth == 0 and index > 0
              and (text[index - 1].isdigit() or text[index - 1] in ')].')):
            terms.append((sign, text[start:index]))
            sign = 1 if character == '+' else -1
            start = index + 1
    terms.append((sign, text[start:]))
    return terms


def _strip_imaginary_unit(term):
    """(is_imaginary, remaining_text). Accepts `i*A`, `A*i`, `Ai` and bare `i`."""
    if term in ('i', 'I'):
        return (True, '1')
    lowered = term.lower()
    if lowered.startswith('i*'):
        return (True, term[2:])
    if lowered.endswith('*i'):
        return (True, term[:-2])
    if lowered.endswith('i'):
        #No real-number format ends in 'i', so this is unambiguous -- and it is
        #what people actually type.
        return (True, term[:-1])
    return (False, term)


def parse_complex(text):
    """Parse the documented complex grammar into an `ExactComplex`.

    At most one real and one imaginary term. Summing several terms on an axis
    would require arithmetic on notations -- the sum of two decimal expansions
    is not itself an expansion -- and the documented grammar does not ask for
    it, so it is refused rather than silently reinterpreted.
    """
    if not isinstance(text, str):
        raise ParseError('expected text')
    stripped = text.strip().replace(' ', '')
    if not stripped:
        raise ParseError('empty')

    real_part = None
    imaginary_part = None

    for sign, term in _split_terms(stripped):
        if not term:
            continue
        is_imaginary, remaining = _strip_imaginary_unit(term)
        if not remaining:
            remaining = '1'

        value = parse_real(remaining)
        if sign < 0:
            value = -value

        if is_imaginary:
            if imaginary_part is not None:
                raise ParseError('more than one imaginary term: %r' % (text,))
            imaginary_part = value
        else:
            if real_part is not None:
                raise ParseError('more than one real term: %r' % (text,))
            real_part = value

    if real_part is None:
        real_part = parse_real('0')
    if imaginary_part is None:
        imaginary_part = parse_real('0')

    return ExactComplex(real_part, imaginary_part)
