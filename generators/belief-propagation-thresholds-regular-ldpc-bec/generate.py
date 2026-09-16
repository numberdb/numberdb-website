"""Belief-propagation thresholds of regular LDPC codes on the binary erasure channel -- numberdb.org/T275.

For 3 <= l < r, epsilon^BP_{l,r} is the binary-erasure-channel threshold
of the regular (l,r) low-density parity-check ensemble under
belief-propagation decoding. Kudekar, Richardson and Urbanke characterize it
by

    epsilon^BP_{l,r} = x / (1 - (1 - x)^(r - 1))^(l - 1),

where x is the positive root of

    p(x) = ((l - 1)(r - 1) - 1)(1 - x)^(r - 2)
           - sum_{i=0}^{r-3} (1 - x)^i.

This table stores epsilon^BP_{l,r} for every 3 <= l < r <= 12 at 100 digits
in ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The root x^BP_{l,r} is enclosed by bisection on the sign of p(x), with the
signs at the two ends checked in ball arithmetic. The bracket has half-width
10^-(digits+6), and evaluating epsilon(x) on the ball around that bracket
encloses the value written to the table.
"""

import os
import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T275")

# Measured before filling the draft: 45 entries, longest value under 130
# characters, and an entries block of about 14 KB including comments.
L_MIN = 3
R_MAX = 12

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every result ball has radius below 6e-106.
WORKING_GUARD = 64

# Decimal places of the bracket around the root beyond the digits written.
BRACKET_GUARD = 6

COMMENT_DIGITS = 12

PUBLISHED_VALUES = {
    (3, 6): "0.42944",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def p_bp(x, l, r):
    """The sign-changing polynomial whose positive zero is x^BP_{l,r}."""
    parent = x.parent()
    y = parent(1) - x
    total = parent(0)
    term = parent(1)
    for i in range(r - 2):
        if i:
            term *= y
        total += term
    return ((l - 1) * (r - 1) - 1) * y ** (r - 2) - total


def epsilon_from_x(x, l, r):
    """The BEC erasure probability on the density-evolution threshold curve."""
    return x / (1 - (1 - x) ** (r - 1)) ** (l - 1)


def root(l, r, digits):
    """A ball enclosing x^BP_{l,r}, found by bisection with sign checks."""
    if l < 3:
        raise ValueError("the table starts at variable degree l >= 3")
    if r <= l:
        raise ValueError("the table uses positive-rate pairs with r > l")

    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo, hi = RR(0), RR(1)

    if not (p_bp(RBF(lo), l, r) > 0 and p_bp(RBF(hi), l, r) < 0):
        raise ArithmeticError("root was not bracketed for l=%s, r=%s" % (l, r))

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        value = p_bp(RBF(mid), l, r)
        if value.contains_zero():
            raise ArithmeticError("could not decide root sign at x=%s for l=%s, r=%s" % (mid, l, r))
        if value > 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = p_bp(RBF(x0 - delta), l, r)
    right = p_bp(RBF(x0 + delta), l, r)
    if not (left > 0 and right < 0):
        raise ArithmeticError("no sign change across root bracket for l=%s, r=%s" % (l, r))
    return RBF(x0).add_error(delta)


def threshold(l, r, digits):
    """(epsilon^BP_{l,r}, x^BP_{l,r}) as real balls."""
    x = root(l, r, digits)
    value = epsilon_from_x(x, l, r)
    if not (0 < value and value < 1):
        raise ArithmeticError("threshold came out as %s at x=%s for l=%s, r=%s" % (value, x, l, r))
    return value, x


class LDPCBeliefPropagationThresholds(numberdb.Generator):
    """Generator for T275, the table of regular LDPC BP thresholds on the BEC."""

    table = TABLE
    parameters = ("l", "r")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for l in range(L_MIN, R_MAX):
            for r in range(l + 1, R_MAX + 1):
                yield {"l": str(l), "r": str(r)}

    def value(self, params, digits):
        l = int(params["l"])
        r = int(params["r"])
        value, x = threshold(l, r, digits)
        comment = r"The double fixed point is $x^{\mathrm{BP}}_{%d,%d}=%s$." % (
            l,
            r,
            to_text(x, COMMENT_DIGITS),
        )
        expected = PUBLISHED_VALUES.get((l, r))
        if expected is not None:
            comment += (
                r" Kudekar, Richardson and Urbanke give "
                r"$\epsilon^{\mathrm{BP}}_{%d,%d}\approx %s$ CITE{KRU}."
                % (l, r, expected)
            )
        return {"number": value, "comment": comment}


def _mpmath_threshold(l, r, digits=120):
    """Independent numerical minimisation of epsilon(x) on (0,1]."""
    from mpmath import mp

    mp.dps = digits + 30

    def eps(x):
        return x / (1 - (1 - x) ** (r - 1)) ** (l - 1)

    lo, hi = mp.mpf("1e-40"), mp.mpf(1)
    invphi = (mp.sqrt(5) - 1) / 2
    invphi2 = (3 - mp.sqrt(5)) / 2
    h = hi - lo
    c = lo + invphi2 * h
    d = lo + invphi * h
    yc, yd = eps(c), eps(d)

    for _ in range(8 * digits):
        if yc < yd:
            hi, d, yd = d, c, yc
            h *= invphi
            c = lo + invphi2 * h
            yc = eps(c)
        else:
            lo, c, yc = c, d, yd
            h *= invphi
            d = lo + invphi * h
            yd = eps(d)

    return eps((lo + hi) / 2)


def _round_decimal(text, places):
    return Decimal(text).quantize(Decimal("1e-%d" % places))


def run_integrity_checks():
    """Checks that do not use the generator's derivative polynomial."""
    bits = numberdb.bits(120, losing=WORKING_GUARD)
    RBF = RealBallField(bits)
    tolerance = RBF("1e-95")

    for l in range(L_MIN, R_MAX):
        for r in range(l + 1, R_MAX + 1):
            value, _ = threshold(l, r, 100)
            independent_value = _mpmath_threshold(l, r)
            independent = RBF(str(independent_value))
            if not (abs(value - independent) < tolerance):
                raise ArithmeticError("mpmath minimisation failed for l=%d, r=%d" % (l, r))

            expected = PUBLISHED_VALUES.get((l, r))
            if expected is None:
                continue
            places = len(expected.split(".")[1])
            rounded = _round_decimal(str(independent_value), places)
            if str(rounded) != expected:
                raise ArithmeticError(
                    "published value check failed for l=%d, r=%d: %s != %s"
                    % (l, r, rounded, expected)
                )


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries, to_text

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)

        written = to_text(value, wanted, generator.format)
        _check_precision(table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    answer = submit_entries(
        table,
        entries,
        message=message,
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = LDPCBeliefPropagationThresholds()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "regular LDPC belief-propagation thresholds on the binary erasure "
                "channel for 3 <= l < r <= 12"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
