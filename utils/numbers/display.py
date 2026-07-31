"""The uniform view: every number rendered on the same real line.

Search results show values of different kinds side by side, so they are
rendered comparably rather than each in its own notation. That is what
``Number.str_short`` has always done -- it routes through
``str_as_real_interval`` -- and it is deliberate: a column of results is easier
to scan when everything is on one footing.

This is the plain-Python replacement for that path, so rendering a search result
no longer needs Sage.

It is *not* the faithful rendering. The faithful value is ``exact_text``, and
``ExactReal.render()`` produces it. This module answers a different question:
"where does this sit on the real line, to a comparable precision".

One deliberate difference from the Sage version. Exact values are rendered
exactly: -1/2 appears as ``-1/2``, where the old path produced
``-0.50000000000000000``. Under the documented convention a value containing
'.' or 'e' *is* an interval, so rendering an exact rational as a long decimal
now asserts something false -- it says "known to seventeen places, last digit
uncertain" about a number that is known perfectly.
"""

from decimal import Decimal
from fractions import Fraction

from .real import (_format_decimal_exact,
                   _format_decimal_preserving_significance)

__all__ = ['uniform_real_text', 'uniform_complex_text', 'SIGNIFICANT_DIGITS',
           'EXPANSION_THRESHOLD', 'MAX_SIGNIFICANT_DIGITS']

#: Significant digits kept in the bracket form. Matches what the Sage path
#: produced via RealField(15), e.g. [3.129,3.151].
SIGNIFICANT_DIGITS = 4

#: Below this relative diameter a value is tight enough to show as a decimal
#: expansion rather than a bracketed interval.
EXPANSION_THRESHOLD = Fraction(1, 1000)

#: Most significant digits shown. This view exists to be scannable in a column
#: of results, and stored values run to hundreds of digits -- the Riemann zeros
#: carry 31, pi carries 300. Truncating is always a *widening*, so it stays
#: sound: fewer digits claim less, never more. The faithful value is in
#: exact_text and on the table page; this is the summary.
#:
#: Seventeen keeps roughly what the previous float-backed rendering showed, so
#: result columns do not suddenly change width.
MAX_SIGNIFICANT_DIGITS = 17


def _decimal_exponent_at_least(value):
    """Smallest integer e with 10**e >= value, for a positive Fraction."""
    exponent = 0
    if value <= 0:
        return 0
    while Fraction(10) ** exponent < value:
        exponent += 1
    while Fraction(10) ** (exponent - 1) >= value:
        exponent -= 1
    return exponent


def _round_outward(value, exponent, upward):
    """Round to a multiple of 10**exponent, away from the interval's interior."""
    scale = Fraction(10) ** exponent
    scaled = value / scale
    if upward:
        multiple = -((-scaled.numerator) // scaled.denominator)
    else:
        multiple = scaled.numerator // scaled.denominator
    return Fraction(multiple) * scale


def _as_decimal(multiple_of, exponent):
    """A Fraction that is an exact multiple of 10**exponent, as a Decimal.

    The digit count is preserved, which is what carries the precision: the
    Decimal keeps ``exponent`` as its own exponent rather than normalising it
    away.
    """
    digits = multiple_of / (Fraction(10) ** exponent)
    assert digits.denominator == 1
    return Decimal(digits.numerator).scaleb(exponent)


def _format_expansion(multiple_of, exponent):
    """A value whose last digit may be off by one.

    For a negative exponent the faithful formatter is used directly. For a
    non-negative one it would emit ``10000000e14`` -- correct, and the right
    choice when storing, since it keeps "42e0" distinct from the exact integer
    "42". Here the value is only being displayed, so the mantissa is normalised
    to one digit before the point: ``1.0000001e21``. Same digits, same unit in
    the last place, easier to read in a column of results.
    """
    value = _as_decimal(multiple_of, exponent)
    if exponent < 0:
        return _format_decimal_preserving_significance(value)

    sign, digits, _ = value.as_tuple()
    text = ''.join(str(digit) for digit in digits)
    prefix = '-' if sign else ''
    scientific_exponent = exponent + len(text) - 1
    if len(text) == 1:
        return '%s%se%d' % (prefix, text, scientific_exponent)
    return '%s%s.%se%d' % (prefix, text[0], text[1:], scientific_exponent)


def _format_endpoint(multiple_of, exponent):
    """An interval endpoint, which is exact by definition."""
    return _format_decimal_exact(_as_decimal(multiple_of, exponent))


def _significant_exponent(magnitude, digits):
    """Exponent of the last of ``digits`` significant figures of ``magnitude``."""
    if magnitude == 0:
        return 0
    leading = _decimal_exponent_at_least(magnitude)
    return leading - digits


def uniform_real_text(low, high):
    """Render the interval [low, high] (exact Fractions) on the real line.

    Exact values render exactly. Otherwise the value is shown as a decimal
    expansion when it is tight enough for one to be both sound and informative,
    and as a bracketed interval when it is not -- the same two cases the Sage
    path chose between, and for the same reason: a decimal expansion whose
    last digit is uncertain conveys nothing once the uncertainty is larger than
    the digits shown.
    """
    low = Fraction(low)
    high = Fraction(high)
    if low > high:
        low, high = high, low

    if low == high:
        #Exact: no interval to communicate. Shown in full when it is short
        #enough to read, and otherwise summarised as an expansion -- which is
        #a widening, so it still says nothing false, only less.
        text = str(low.numerator) if low.denominator == 1 else str(low)
        if len(text.lstrip('-')) <= MAX_SIGNIFICANT_DIGITS + 1:
            return text
        return _summarise_exact(low)

    radius = (high - low) / 2
    centre = (high + low) / 2

    #Containing zero, relative precision is meaningless, so show the endpoints.
    if low <= 0 <= high:
        return _bracket(low, high)

    relative = (high - low) / abs(centre)
    if relative >= EXPANSION_THRESHOLD:
        return _bracket(low, high)

    #A decimal expansion says "this digit may be off by one", so the shown
    #value plus or minus one unit in the last place must cover [low, high].
    #
    #10**e >= 2*radius always suffices, but only because it assumes the worst
    #case for where the centre rounds. Usually a finer place works, so the
    #tightest one that genuinely contains the interval is chosen instead --
    #showing 3.1415927 rather than 3.141593 for the same value.
    #Never finer than the digit budget, however precisely the value is known.
    coarsest_shown = (_decimal_exponent_at_least(abs(centre))
                      - MAX_SIGNIFICANT_DIGITS)
    exponent = max(_decimal_exponent_at_least(radius) - 1, coarsest_shown)
    for _ in range(40):
        scale = Fraction(10) ** exponent
        nearest = Fraction(round(centre / scale)) * scale
        if nearest - scale <= low and nearest + scale >= high:
            return _format_expansion(nearest, exponent)
        exponent += 1
    #Unreachable in practice: widening by a place always converges, since a
    #large enough unit swallows any bounded interval.
    return _bracket(low, high)


def _summarise_exact(value):
    """An exact value too long to show in full, as a truncated expansion."""
    exponent = _decimal_exponent_at_least(abs(value)) - MAX_SIGNIFICANT_DIGITS
    scale = Fraction(10) ** exponent
    nearest = Fraction(round(value / scale)) * scale
    return _format_expansion(nearest, exponent)


def uniform_complex_text(real_bounds, imaginary_bounds):
    """Both components on the same footing, each capped the same way."""
    real_text = uniform_real_text(*real_bounds)
    imaginary_low, imaginary_high = imaginary_bounds
    if imaginary_high < 0:
        return '%s - %s*I' % (real_text,
                              uniform_real_text(-imaginary_high, -imaginary_low))
    return '%s + %s*I' % (real_text,
                          uniform_real_text(imaginary_low, imaginary_high))


def _bracket(low, high):
    magnitude = max(abs(low), abs(high))
    exponent = _significant_exponent(magnitude, SIGNIFICANT_DIGITS)
    return '[%s,%s]' % (
        _format_endpoint(_round_outward(low, exponent, upward=False), exponent),
        _format_endpoint(_round_outward(high, exponent, upward=True), exponent),
    )
