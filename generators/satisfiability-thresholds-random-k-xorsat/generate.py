"""Satisfiability thresholds of random $k$-XORSAT -- numberdb.org/T272.

For k >= 3, alpha_k is the threshold density m/n for satisfiability of a
random k-XORSAT formula with n variables and m equations, each equation
choosing k distinct variables and a uniform right-hand side. Pittel and
Sorkin give

    alpha_k = xi_k / (k (1 - exp(-xi_k))^(k - 1)),

where xi_k is the positive solution of

    k = xi (1 - exp(-xi)) / (1 - exp(-xi) - xi exp(-xi)).

This table stores alpha_k for 3 <= k <= 12 at 100 digits in ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The root xi_k is enclosed by bisection on psi(x) - k, with the signs at the
two ends checked in ball arithmetic. The bracket has half-width
10^-(digits+6), and evaluating alpha_k on the ball around that bracket
encloses the value written to the table.
"""

import os
import sys

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T272")

# Measured before filling the draft: k = 3..12 gives 10 entries, the longest
# entry is under 260 characters, and the entries block is under 4 KB.
K_MAX = 12

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every result ball has radius below 3e-106.
WORKING_GUARD = 64

# Decimal places by which the bracket around xi_k is narrower than the values
# written. The derivative of alpha at xi_k is harmless on this range.
BRACKET_GUARD = 6

COMMENT_DIGITS = 12

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
        raise ValueError("the XORSAT threshold here is defined for k >= 3")
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo, hi = RR(1), RR(4 * k + 10)
    if not (root_function(RBF(lo), k) < 0 and root_function(RBF(hi), k) > 0):
        raise ArithmeticError("root was not bracketed for k = %s" % k)

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        v = root_function(RBF(mid), k)
        if v.contains_zero():
            raise ArithmeticError("could not decide root sign at x = %s for k = %s" % (mid, k))
        if v < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = root_function(RBF(x0 - delta), k)
    right = root_function(RBF(x0 + delta), k)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across xi_k bracket for k = %s" % k)
    return RBF(x0).add_error(delta)


def threshold(k, digits):
    """(alpha_k, xi_k) as real balls."""
    xi = root(k, digits)
    alpha = alpha_from_xi(xi, k)
    if not (0 < alpha and alpha < 1):
        raise ArithmeticError("threshold came out as %s at xi = %s for k = %s" % (alpha, xi, k))
    return alpha, xi


class XORSATSatisfiabilityThresholds(numberdb.Generator):

    table = TABLE
    parameters = ("k",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for k in range(3, K_MAX + 1):
            yield {"k": str(k)}

    def value(self, params, digits):
        k = int(params["k"])
        alpha, xi = threshold(k, digits)
        if k in PUBLISHED_TEN_DIGITS:
            comment = (
                r"The root is $\xi_{%d}=%s$; Dietzfelbinger, Goerdt, "
                r"Mitzenmacher, Montanari, Pagh and Rink tabulate this "
                r"threshold as $%s$ to ten decimal places CITE{DGMMPR}."
                % (k, to_text(xi, COMMENT_DIGITS), PUBLISHED_TEN_DIGITS[k])
            )
        else:
            comment = r"The root is $\xi_{%d}=%s$." % (k, to_text(xi, COMMENT_DIGITS))
        return {"number": alpha, "comment": comment}


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
    generator = XORSATSatisfiabilityThresholds()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "random k-XORSAT satisfiability thresholds alpha_k for 3 <= k <= 12, "
                "with the defining root enclosed in ball arithmetic"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
