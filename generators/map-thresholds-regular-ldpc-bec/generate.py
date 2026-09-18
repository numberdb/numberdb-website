"""MAP thresholds of regular LDPC codes on the binary erasure channel -- numberdb.org/T276.

For 3 <= l < r, epsilon^MAP_{l,r} is the binary-erasure-channel threshold
of the regular (l,r) low-density parity-check ensemble under maximum a
posteriori decoding. Kudekar, Richardson and Urbanke characterize it by

    epsilon^MAP_{l,r} = x / (1 - (1 - x)^(r - 1))^(l - 1),

where x is the root in (0,1) of

    p(x) = x + (1/r)(1 - x)^(r - 1)(l + l(r - 1)x - r x) - l/r.

This table stores epsilon^MAP_{l,r} for every 3 <= l < r <= 12 at 100
digits in ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The root x^MAP_{l,r} is enclosed by bisection on the sign of p(x) in the
interval (0,1), with the signs at the two ends checked in ball arithmetic.
The bracket has half-width 10^-(digits+6), and evaluating epsilon(x) on the
ball around that bracket encloses the value written to the table.
"""

import os
import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T276")

# Same rectangle as the sibling BP table T275.
L_MIN = 3
R_MAX = 12

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every result ball has radius below 6e-106.
WORKING_GUARD = 64

# Decimal places of the bracket around the root beyond the digits written.
BRACKET_GUARD = 6

COMMENT_DIGITS = 12

PUBLISHED_VALUES = {
    (3, 6): "0.488151",
    (4, 8): "0.49774",
    (5, 10): "0.499486",
    (6, 12): "0.499876",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def p_map(x, l, r):
    """The sign-changing polynomial whose root in (0,1) is x^MAP_{l,r}."""
    parent = x.parent()
    y = parent(1) - x
    return (
        x
        + y ** (r - 1) * (parent(l) + parent(l * (r - 1)) * x - parent(r) * x) / parent(r)
        - parent(l) / parent(r)
    )


def epsilon_from_x(x, l, r):
    """The BEC erasure probability on the density-evolution threshold curve."""
    return x / (1 - (1 - x) ** (r - 1)) ** (l - 1)


def trial_entropy_condition(x, l, r):
    """The Maxwell trial-entropy equation, zero at x^MAP_{l,r}."""
    parent = x.parent()
    y = parent(1) - x
    one_minus = parent(1) - y ** (r - 1)
    return (
        epsilon_from_x(x, l, r) * one_minus ** l
        + parent(l) * x * y ** (r - 1)
        - parent(l) / parent(r) * (parent(1) - y ** r)
    )


def _find_negative_left_endpoint(l, r, RBF, RR):
    """A point in (0,1) where p_map is negative, away from the zero at 0."""
    candidates = [RR(10) ** (-e) for e in range(6, 0, -1)]
    candidates.extend(RR(i) / RR(100) for i in range(10, 100))
    for candidate in candidates:
        value = p_map(RBF(candidate), l, r)
        if value.contains_zero():
            continue
        if value < 0:
            return candidate
    raise ArithmeticError("could not find a negative point for l=%s, r=%s" % (l, r))


def root(l, r, digits):
    """A ball enclosing x^MAP_{l,r}, found by bisection with sign checks."""
    if l < 3:
        raise ValueError("the table starts at variable degree l >= 3")
    if r <= l:
        raise ValueError("the table uses positive-rate pairs with r > l")

    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo = _find_negative_left_endpoint(l, r, RBF, RR)
    hi = RR(1)

    if not (p_map(RBF(lo), l, r) < 0 and p_map(RBF(hi), l, r) > 0):
        raise ArithmeticError("root was not bracketed for l=%s, r=%s" % (l, r))

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        value = p_map(RBF(mid), l, r)
        if value.contains_zero():
            raise ArithmeticError("could not decide root sign at x=%s for l=%s, r=%s" % (mid, l, r))
        if value < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = p_map(RBF(x0 - delta), l, r)
    right = p_map(RBF(x0 + delta), l, r)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across root bracket for l=%s, r=%s" % (l, r))
    return RBF(x0).add_error(delta)


def threshold(l, r, digits):
    """(epsilon^MAP_{l,r}, x^MAP_{l,r}) as real balls."""
    x = root(l, r, digits)
    value = epsilon_from_x(x, l, r)
    if not (0 < value and value < 1):
        raise ArithmeticError("threshold came out as %s at x=%s for l=%s, r=%s" % (value, x, l, r))
    return value, x


class LDPCMAPThresholds(numberdb.Generator):
    """Generator for T276, the table of regular LDPC MAP thresholds on the BEC."""

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
        comment = r"The Maxwell root is $x^{\mathrm{MAP}}_{%d,%d}=%s$." % (
            l,
            r,
            to_text(x, COMMENT_DIGITS),
        )
        expected = PUBLISHED_VALUES.get((l, r))
        if expected is not None:
            comment += (
                r" Kudekar, Richardson and Urbanke give "
                r"$\epsilon^{\mathrm{MAP}}_{%d,%d}\approx %s$ CITE{KRU}."
                % (l, r, expected)
            )
        return {"number": value, "comment": comment}


def _mpmath_trial_threshold(l, r, digits=120):
    """Independent numerical value using the trial-entropy equation."""
    from mpmath import mp

    mp.dps = digits + 30

    def eps(x):
        return x / (1 - (1 - x) ** (r - 1)) ** (l - 1)

    def trial(x):
        y = 1 - x
        return eps(x) * (1 - y ** (r - 1)) ** l + l * x * y ** (r - 1) - mp.mpf(l) / r * (1 - y ** r)

    lo = mp.mpf("1e-6")
    while trial(lo) >= 0:
        lo *= 10
        if lo >= mp.mpf("0.9"):
            raise ArithmeticError("could not find negative trial value for l=%d, r=%d" % (l, r))
    hi = mp.mpf(1)
    if trial(hi) <= 0:
        raise ArithmeticError("right endpoint did not bracket the MAP root for l=%d, r=%d" % (l, r))

    for _ in range(4 * digits):
        mid = (lo + hi) / 2
        if trial(mid) < 0:
            lo = mid
        else:
            hi = mid

    return eps((lo + hi) / 2)


def _round_decimal(text, places):
    return Decimal(text).quantize(Decimal("1e-%d" % places))


def run_integrity_checks():
    """Checks that do not use the generator's MAP-polynomial implementation."""
    bits = numberdb.bits(120, losing=WORKING_GUARD)
    RBF = RealBallField(bits)
    tolerance = RBF("1e-95")

    bp_values = None
    try:
        bp_values = numberdb.table("T275")["Numbers"]
    except Exception:  # noqa: BLE001
        bp_values = None

    for l in range(L_MIN, R_MAX):
        for r in range(l + 1, R_MAX + 1):
            value, x = threshold(l, r, 100)

            trial = trial_entropy_condition(x, l, r)
            if not trial.contains_zero():
                raise ArithmeticError("trial-entropy condition failed for l=%d, r=%d" % (l, r))

            independent_value = _mpmath_trial_threshold(l, r)
            independent = RBF(str(independent_value))
            if not (abs(value - independent) < tolerance):
                raise ArithmeticError("mpmath trial-entropy check failed for l=%d, r=%d" % (l, r))

            expected = PUBLISHED_VALUES.get((l, r))
            if expected is not None:
                places = len(expected.split(".")[1])
                rounded = _round_decimal(str(independent_value), places)
                if str(rounded) != expected:
                    raise ArithmeticError(
                        "published value check failed for l=%d, r=%d: %s != %s"
                        % (l, r, rounded, expected)
                    )

            if bp_values is not None:
                bp = RBF(bp_values[str(l)][str(r)]["number"])
                capacity = RBF(l) / RBF(r)
                if not (bp < value and value < capacity):
                    raise ArithmeticError("BP < MAP < capacity failed for l=%d, r=%d" % (l, r))


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
    generator = LDPCMAPThresholds()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "regular LDPC MAP thresholds on the binary erasure channel "
                "for 3 <= l < r <= 12"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
