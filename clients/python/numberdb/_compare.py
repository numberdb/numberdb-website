"""Whether two written values disagree, as opposed to being written differently.

A stored value and a freshly computed one are two claims about one number, made
to whatever precision each was made to. The question worth asking is not "are
these the same string" but "can both be true".

Text equality answers the wrong one. ``3.14159`` and ``3.141592653589793`` are
the same number known to different precision, and a check that calls them
different reports every entry of a table as broken the moment a generator is
run at a different precision than the table was built at -- which then proposes
rewriting entries that were never wrong.

So values are read as what they claim: a centre and how far the claim reaches.
The corpus writes that four ways, and all four appear in it:

    3670.48296788(13)      uncertainty in the last digits, as physics writes it
    14.13472514 +/- 1e-8   a ball, as Arb writes it
    3.14159?               one unit in the last place, as Sage writes it
    -24.4825958537565077   a plain decimal, precise to the digits written

Two claims contradict when the intervals they describe do not meet. Anything
else is agreement, possibly at different precision, and the difference in
precision is itself worth reporting -- replacing a hundred stored digits with
fifty is a loss, and usually a mistake, but it is not a contradiction.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from typing import Optional, Tuple

__all__ = ['SAME', 'REFINES', 'COARSENS', 'AGREES', 'CONTRADICTS', 'UNREADABLE',
           'EXACT', 'compare', 'digits_of']

#: The two values are written identically.
SAME = 'same'
#: They agree, and the new one says more than the stored one.
REFINES = 'refines'
#: They agree, and the new one says less -- a hundred digits replaced by fifty.
COARSENS = 'coarsens'
#: They agree, to the same precision, without being the same text.
AGREES = 'agrees'
#: They cannot both be true.
CONTRADICTS = 'contradicts'
#: Not numbers this module can read -- a polynomial, an expression, a symbol.
UNREADABLE = 'unreadable'

#: What `digits_of` reports for a value that is exact. Not infinity, because
#: it is compared with counts and has to stay an integer, and not a float,
#: because these numbers are the one thing here that must not become floats.
EXACT = 10 ** 9

#: Enough room to subtract two values of the length the corpus actually holds;
#: its longest exact value runs to 54,342 digits, but those are polynomial
#: coefficients, which are compared as text rather than as decimals.
_PRECISION = 2000

_BALL = re.compile(r'^\s*(?P<centre>[^+]+?)\s*\+/-\s*(?P<radius>\S+)\s*$')
_BRACKETED = re.compile(r'^\s*(?P<centre>[-+]?[\d.]+)\((?P<error>\d+)\)'
                        r'(?:[eE](?P<exponent>[-+]?\d+))?\s*$')
_DECIMAL = re.compile(r'^\s*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?\s*$')


def compare(stored: str, produced: str) -> str:
    """How a freshly computed value stands to the one already stored.

    Returns one of the constants above. `CONTRADICTS` is the only one that
    means something is wrong; `COARSENS` means something was lost.
    """
    stored = (stored or '').strip()
    produced = (produced or '').strip()
    if stored == produced:
        return SAME
    if not stored or not produced:
        return UNREADABLE

    #A complex value is two claims side by side, and contradicting in either
    #part contradicts. 'a + i * b' is how this database writes them.
    stored_parts = _complex_parts(stored)
    produced_parts = _complex_parts(produced)
    if stored_parts and produced_parts:
        return _worst(compare(stored_parts[0], produced_parts[0]),
                      compare(stored_parts[1], produced_parts[1]))

    #Exact values have no precision to differ in: 1/3 and 0.333 are not the
    #same number, and a rational that changed is a contradiction, not a
    #refinement.
    stored_exact = _as_fraction(stored)
    produced_exact = _as_fraction(produced)
    if stored_exact is not None and produced_exact is not None:
        return SAME if stored_exact == produced_exact else CONTRADICTS

    stored_claim = _claim(stored)
    produced_claim = _claim(produced)
    if stored_claim is None or produced_claim is None:
        #A p-adic carries its own precision in an O-term, so two of them are
        #comparable even though neither is a decimal.
        verdict = _compare_p_adic(stored, produced)
        if verdict is not None:
            return verdict
        #A polynomial or a symbolic expression. One being a truncation of the
        #other is the recognisable case of "the same, to less precision";
        #beyond that this module declines to guess, because calling two things
        #it cannot read a contradiction would stop runs over a spelling.
        if produced.startswith(stored):
            return REFINES
        if stored.startswith(produced):
            return COARSENS
        return UNREADABLE

    stored_centre, stored_reach = stored_claim
    produced_centre, produced_reach = produced_claim

    with localcontext() as context:
        context.prec = _PRECISION
        apart = abs(stored_centre - produced_centre)
        if apart > stored_reach + produced_reach:
            return CONTRADICTS

    stored_digits = digits_of(stored)
    produced_digits = digits_of(produced)

    #The same number written two ways loses nothing, even when one writing is
    #exact and the other is not. Without this, a complex value whose real part
    #is stored as `1` and recomputed as `1.000` counts as a loss of precision
    #and stops the run -- and parts written as 0 or 1 are everywhere in a
    #table of complex numbers.
    if apart == 0 and stored_digits == EXACT and produced_digits != EXACT:
        return AGREES

    if produced_digits > stored_digits:
        return REFINES
    if produced_digits < stored_digits:
        return COARSENS
    return AGREES


def digits_of(text: str) -> int:
    """How many significant digits a written value claims.

    Taken from how far the claim reaches rather than from how much was typed,
    so ``14.13 +/- 1e-9`` counts as the ten digits it asserts and not as the
    four it prints. Where there is no reach to measure -- a polynomial, an
    expression -- it falls back to counting, leading zeros excluded, since
    those place a number rather than say anything about it.
    """
    text = (text or '').strip()
    parts = _complex_parts(text)
    if parts:
        #A complex value is as precise as its weaker part.
        return min(digits_of(parts[0]), digits_of(parts[1]))

    #An exact value states every digit there is. Counting the characters of
    #'1/3' as two digits would make 0.3334 look like a refinement of it, when
    #replacing an exact rational with four decimals is the plainest loss of
    #precision there is.
    if _as_fraction(text) is not None:
        return EXACT

    claim = _claim(text)
    if claim is not None:
        centre, reach = claim
        if centre and reach > 0:
            with localcontext() as context:
                context.prec = 40
                try:
                    return max(0, int((abs(centre) / reach).log10()) + 1)
                except (InvalidOperation, ValueError):
                    pass

    p_adic = _P_ADIC.match(text)
    if p_adic:
        return len(_p_adic_terms(p_adic.group('body')))

    ball = _BALL.match(text)
    if ball:
        text = ball.group('centre').strip()
    bracketed = _BRACKETED.match(text)
    if bracketed:
        text = bracketed.group('centre').strip()

    text = text.rstrip('?')
    body = text.split('e')[0].split('E')[0]
    body = body.lstrip('-+').replace('.', '')
    stripped = body.lstrip('0')
    return len(stripped) if stripped else len(body)


_P_ADIC = re.compile(r'^\s*(?P<body>.*?)\s*\+?\s*O\((?P<order>[^)]+)\)\s*$')


def _p_adic_terms(body):
    """The terms a p-adic states, before its O-term says where it stops."""
    return [term.strip() for term in body.split('+') if term.strip()]


def _compare_p_adic(stored: str, produced: str) -> Optional[str]:
    """Two p-adics, which state terms and then say where they stopped.

    They agree when the terms they both state agree; the one that states more
    of them is the more precise. A term that differs inside the range both
    claim is a contradiction, exactly as a differing digit would be.
    """
    stored_match = _P_ADIC.match(stored)
    produced_match = _P_ADIC.match(produced)
    if not stored_match or not produced_match:
        return None

    stored_terms = _p_adic_terms(stored_match.group('body'))
    produced_terms = _p_adic_terms(produced_match.group('body'))
    shared = min(len(stored_terms), len(produced_terms))
    if stored_terms[:shared] != produced_terms[:shared]:
        return CONTRADICTS
    if len(produced_terms) > len(stored_terms):
        return REFINES
    if len(produced_terms) < len(stored_terms):
        return COARSENS
    #Same terms, so whichever says it stopped later knows more: O(3^40) is a
    #claim about more of the number than O(3^20).
    stored_order = _order(stored_match.group('order'))
    produced_order = _order(produced_match.group('order'))
    if stored_order is not None and produced_order is not None:
        if produced_order > stored_order:
            return REFINES
        if produced_order < stored_order:
            return COARSENS
    return AGREES


def _order(text):
    """The exponent of an O-term, which is how far a p-adic claims to know."""
    match = re.match(r'^\s*(\d+)\s*\^\s*(-?\d+)\s*$', text or '')
    if not match:
        return None
    return int(match.group(2))


def _worst(*verdicts):
    """The verdict a reader would take away from a value with several parts."""
    for verdict in (CONTRADICTS, UNREADABLE, COARSENS, REFINES, AGREES):
        if verdict in verdicts:
            return verdict
    return SAME


def _complex_parts(text: str) -> Optional[Tuple[str, str]]:
    """``a + i * b`` split into its two claims.

    This database writes the imaginary unit before the coefficient, because the
    coefficient may run to hundreds of digits and a reader should not have to
    reach the end of them to find out which part they were reading.
    """
    for separator in (' + i * ', ' - i * ', '+i*', '-i*'):
        if separator in text:
            real, _, imaginary = text.partition(separator)
            sign = '-' if separator.strip().startswith('-') else ''
            return real.strip(), sign + imaginary.strip()
    return None


def _as_fraction(text: str) -> Optional[Fraction]:
    """An integer or a rational, which are exact and compare exactly."""
    text = text.strip()
    if not re.match(r'^[-+]?\d+(/\d+)?$', text):
        return None
    try:
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None


def _claim(text: str):
    """A written value as (centre, how far the claim reaches), or None.

    The reach is what makes two values comparable across precisions: a value
    written to six digits is not a point, it is a statement about a range, and
    a value written to forty digits sits inside that range or contradicts it.
    """
    text = text.strip()

    #An exact value reaches nowhere: it is the number, not a range around it.
    #Claiming one lets a rational be checked against a decimal, which is what
    #a table of rationals verified by a numeric generator comes down to.
    exact = _as_fraction(text)
    if exact is not None:
        with localcontext() as context:
            context.prec = _PRECISION
            return Decimal(exact.numerator) / Decimal(exact.denominator), \
                Decimal(0)

    ball = _BALL.match(text)
    if ball:
        centre = _decimal(ball.group('centre'))
        radius = _decimal(ball.group('radius'))
        if centre is None or radius is None:
            return None
        return centre, abs(radius)

    bracketed = _BRACKETED.match(text)
    if bracketed:
        #3670.48296788(13): the digits in brackets are the uncertainty in the
        #last digits written, so their size depends on where those digits sit.
        centre = _decimal(bracketed.group('centre'))
        if centre is None:
            return None
        error = Decimal(bracketed.group('error'))
        radius = error * _ulp(bracketed.group('centre'))
        exponent = bracketed.group('exponent')
        if exponent:
            scale = Decimal(1).scaleb(int(exponent))
            centre, radius = centre * scale, radius * scale
        return centre, abs(radius)

    #Sage's question mark: one unit in the last place.
    uncertain = text.endswith('?')
    body = text.rstrip('?')
    if not _DECIMAL.match(body):
        return None
    centre = _decimal(body)
    if centre is None:
        return None
    #A plain decimal is a claim to the digits written, so its reach is the
    #last place. Sage's ?-notation means the same thing said out loud.
    return centre, _ulp(body)


def _ulp(text: str) -> Decimal:
    """One unit in the last place written, which is what a decimal claims."""
    body = text.strip()
    exponent = 0
    for marker in ('e', 'E'):
        if marker in body:
            body, _, tail = body.partition(marker)
            try:
                exponent = int(tail)
            except ValueError:
                exponent = 0
            break
    if '.' in body:
        places = len(body.split('.', 1)[1])
    else:
        places = 0
    return Decimal(1).scaleb(exponent - places)


def _decimal(text: str) -> Optional[Decimal]:
    try:
        with localcontext() as context:
            context.prec = _PRECISION
            return Decimal(text.strip())
    except (InvalidOperation, ValueError):
        return None
