"""Bounding what a request may carry, without ever narrowing it.

A search may be given a number of any size -- an integer of a thousand digits,
an interval known to five hundred -- and sending it whole is neither necessary
nor kind: the server stores nothing to that precision, the URL has a limit, and
one caller can make the machine work arbitrarily hard.

So a query is trimmed to a hundred significant decimal digits. The direction is
the whole point: the lower bound is rounded **down** and the upper bound
**up**, so the interval sent always contains the interval meant. A query can
therefore return more than it strictly needed to, and never less -- trimming
inward would silently hide the number the caller was looking for.

An exact value too long to send becomes an interval. That is a real change of
meaning, and the honest one: an integer of a thousand digits cannot be conveyed
in a hundred, so it is conveyed as the range it is known to lie in. The server
searches exact values as point intervals anyway, so nothing is lost that was
being used.

p-adics are counted in their own digits. A hundred decimal digits is worth
``100 * log(10) / log(p)`` of them -- 333 for p = 2, 143 for p = 5, and fewer
than two for a prime past 10^50, where the floor of two digits applies instead.
"""

import math
from fractions import Fraction
from typing import Tuple, Union

Bound = Union[Fraction, float]

__all__ = ['SIGNIFICANT_DIGITS', 'MAX_BATCH', 'bound_interval',
           'p_adic_digits', 'Bound']

#: Significant decimal digits a query may carry. Well past anything stored:
#: the most precise values in the database run to a few hundred, and a search
#: is a question about identity, not a transcription.
SIGNIFICANT_DIGITS = 100

#: Numbers in one batched request.
MAX_BATCH = 100

#: Fewest p-adic digits a query keeps, however large the prime. Past about
#: 10^50 a single digit already carries more than a hundred decimal ones, and
#: one digit is a weak question; two keeps it meaningful.
MIN_P_ADIC_DIGITS = 2


def _is_infinite(value: Bound) -> bool:
    return isinstance(value, float) and math.isinf(value)


def _decimal_exponent(value: Fraction) -> int:
    """The position of the leading decimal digit of a positive value."""
    if value <= 0:
        return 0
    exponent = 0
    while Fraction(10) ** exponent <= value:
        exponent += 1
    while Fraction(10) ** (exponent - 1) > value:
        exponent -= 1
    return exponent


def bound_interval(lower: Bound, upper: Bound,
                   digits: int = SIGNIFICANT_DIGITS) -> Tuple[Bound, Bound]:
    """``[lower, upper]`` trimmed to ``digits`` significant digits, outward.

    Returns the interval unchanged when it is already short enough, so an
    ordinary query is not perturbed at all.
    """
    if lower > upper:
        lower, upper = upper, lower

    #An unbounded end is already as coarse as an end can be, and there is
    #nothing to trim. Left alone deliberately: asking for the leading decimal
    #digit of an infinity does not terminate.
    if _is_infinite(lower) or _is_infinite(upper):
        return lower, upper

    #Finite past the guard above, so exact from here on.
    low_exact, high_exact = Fraction(lower), Fraction(upper)
    magnitude = max(abs(low_exact), abs(high_exact))
    if magnitude == 0:
        return low_exact, high_exact

    #The place value of the last digit kept.
    exponent = _decimal_exponent(magnitude) - digits
    scale = Fraction(10) ** exponent
    if scale == 0:
        return low_exact, high_exact

    #Floor for the lower end, ceiling for the upper: the result contains the
    #original, whatever the signs.
    low = Fraction(_floor_div(low_exact, scale)) * scale
    high = Fraction(-_floor_div(-high_exact, scale)) * scale
    if low > low_exact or high < high_exact:  # pragma: no cover - the claim
        raise AssertionError('bounding narrowed an interval')
    return low, high


def _floor_div(value: Fraction, scale: Fraction) -> int:
    scaled = value / scale
    return scaled.numerator // scaled.denominator


def p_adic_digits(prime: int, digits: int = SIGNIFICANT_DIGITS) -> int:
    """How many p-adic digits are worth ``digits`` decimal ones.

    ``digits * log(10) / log(p)``, floored at two: for a prime past 10^50 a
    single digit already says more than a hundred decimal digits, and asking
    about one digit is barely a question.
    """
    if prime < 2:
        raise ValueError('%r is not a prime' % (prime,))
    scaled = int(math.ceil(digits * math.log(10) / math.log(prime)))
    return max(scaled, MIN_P_ADIC_DIGITS)
