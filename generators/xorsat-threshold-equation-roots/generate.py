"""Roots of the $k$-XORSAT threshold equation -- numberdb.org/T287.

For k >= 3, xi_k is the positive solution of

    k = xi (1 - exp(-xi)) / (1 - exp(-xi) - xi exp(-xi)).

This table stores xi_k for 3 <= k <= 12 at 100 digits in ball arithmetic.
The companion satisfiability threshold table is T272.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The root xi_k is enclosed by bisection on psi(x) - k. The signs at both ends
of the final bracket are checked in ball arithmetic, and that bracket is the
stored enclosure.
"""

import os
import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T287")

# The range follows T272, the companion satisfiability threshold table. The
# source table CITE{DGMMPR} prints k=3..7, and T272 extends the reference range
# to k=12 where alpha_k is already within 4e-4 of 1.
K_MIN = 3
K_MAX = 12

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every result ball has radius below 2e-106.
WORKING_GUARD = 64

# Decimal places by which the bracket around xi_k is narrower than the values
# written.
BRACKET_GUARD = 6

PUBLISHED_TEN_DIGITS = {
    3: "0.9179352767",
    4: "0.9767701649",
    5: "0.9924383913",
    6: "0.9973795528",
    7: "0.9990637588",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def psi(x):
    """x(1-e^-x)/(1-e^-x-xe^-x), the root equation's left side."""
    e = (-x).exp()
    return x * (1 - e) / (1 - e - x * e)


def root_function(x, k):
    """The sign-changing function whose positive zero is xi_k."""
    return psi(x) - k


def alpha_from_xi(x, k):
    """The XORSAT satisfiability threshold from the root xi_k."""
    return x / (k * (1 - (-x).exp()) ** (k - 1))


def root(k, digits):
    """A ball enclosing xi_k, found by bisection with ball sign checks."""
    if k < 3:
        raise ValueError("the XORSAT threshold equation here is defined for k >= 3")
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo, hi = RR(1), RR(4 * k + 10)
    if not (root_function(RBF(lo), k) < 0 and root_function(RBF(hi), k) > 0):
        raise ArithmeticError("root was not bracketed for k = %s" % k)

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        value = root_function(RBF(mid), k)
        if value.contains_zero():
            raise ArithmeticError("could not decide root sign at x = %s for k = %s" % (mid, k))
        if value < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = root_function(RBF(x0 - delta), k)
    right = root_function(RBF(x0 + delta), k)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across xi_k bracket for k = %s" % k)
    return RBF(x0).add_error(delta)


class XORSATThresholdEquationRoots(numberdb.Generator):
    """Generator for T287, the table of roots xi_k."""

    table = TABLE
    parameters = ("k",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for k in range(K_MIN, K_MAX + 1):
            yield {"k": str(k)}

    def value(self, params, digits):
        k = int(params["k"])
        xi = root(k, digits)
        return {
            "number": xi,
            "comment": (
                r"The associated satisfiability threshold is "
                r"HREF{Satisfiability_thresholds_of_random_k-XORSAT#%d}[$\alpha_{%d}$]."
                % (k, k)
            ),
        }


def _mpmath_root(k, digits=120):
    """Independent numerical root using mpmath."""
    from mpmath import mp

    mp.dps = digits + 30

    def mppsi(x):
        e = mp.e ** (-x)
        return x * (1 - e) / (1 - e - x * e)

    left = mp.mpf("1")
    right = mp.mpf(4 * k + 10)
    if not (mppsi(left) - k < 0 and mppsi(right) - k > 0):
        raise ArithmeticError("mpmath root was not bracketed for k=%d" % k)
    for _ in range(4 * digits):
        mid = (left + right) / 2
        if mppsi(mid) - k < 0:
            left = mid
        else:
            right = mid
    return (left + right) / 2


def _round_decimal(text, places):
    return str(Decimal(text).quantize(Decimal("1e-%d" % places)))


def run_integrity_checks():
    """Checks that do not share the generator's ball arithmetic."""
    bits = numberdb.bits(120, losing=WORKING_GUARD)
    RBF = RealBallField(bits)
    tolerance = RBF("1e-95")

    for k in range(K_MIN, K_MAX + 1):
        xi = root(k, 100)
        independent_xi = _mpmath_root(k)
        independent = RBF(str(independent_xi))
        if not (abs(xi - independent) < tolerance):
            raise ArithmeticError("mpmath root comparison failed for k=%d" % k)

        alpha = alpha_from_xi(xi, k)
        expected = PUBLISHED_TEN_DIGITS.get(k)
        if expected is not None:
            places = len(expected.split(".")[1])
            rounded = _round_decimal(to_text(alpha, 30), places)
            if rounded != expected:
                raise ArithmeticError(
                    "threshold comparison failed for k=%d: %s != %s"
                    % (k, rounded, expected)
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
    from numberdb._write import Entries, attach, submit_entries

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
    generator = XORSATThresholdEquationRoots()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="roots of the k-XORSAT threshold equation for 3 <= k <= 12",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
