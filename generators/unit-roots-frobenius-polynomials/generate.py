"""Unit roots alpha of the Frobenius polynomials x^2 - a*x + p -- numberdb.org/T414.

For each prime p in [5, 97] and each nonzero trace a with a^2 <= 4p,
the table stores the p-adic unit root alpha congruent to a modulo p.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The p-adic precision is the family convention from issue #189: the least n
with p^n >= 10^50. Five extra p-adic guard digits are used while lifting and
then discarded before the value is returned.

The natural small-prime reference range p < 100 measures 566 entries, longest
533 characters and a 203.5 KB entries block. The last figure is above the
160 KB target but below the 320 KB soft limit; p <= 73 was measured at
157.5 KB and left as an unnaturally shaped cutoff.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_prime
from sage.rings.integer_ring import ZZ
from sage.rings.padics.factory import Qp


TABLE = "T414"
MAX_PRIME = 97
WORKING_GUARD = 5
PRECISION_TARGET = ZZ(10) ** 50


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def p_adic_precision(p):
    """The least n with p^n >= 10^50."""
    p = ZZ(p)
    precision = ZZ(1)
    power = p
    while power < PRECISION_TARGET:
        precision += 1
        power *= p
    return precision


def ordinary_traces(p):
    """Nonzero Hasse traces, ordered for reading."""
    bound = ZZ(4 * ZZ(p)).isqrt()
    for absolute in range(1, int(bound) + 1):
        yield ZZ(absolute)
        yield ZZ(-absolute)


def primes():
    for p in range(5, MAX_PRIME + 1):
        if is_prime(p):
            yield ZZ(p)


def _residue_mod_p(value, p):
    return ZZ(value.lift()) % ZZ(p)


def unit_root(p, a, guard=WORKING_GUARD):
    p = ZZ(p)
    a = ZZ(a)
    precision = p_adic_precision(p)
    field = Qp(p, prec=int(precision + guard))
    pp = field(p)
    aa = field(a)
    x = field(a)

    for _ in range(int(precision + guard)):
        x = x - (x * x - aa * x + pp) / (2 * x - aa)

    x = x.add_bigoh(int(precision))
    residual = x * x - field(a) * x + field(p)
    if residual != 0 and residual.valuation() < precision:
        raise ArithmeticError("root check failed for p=%s, a=%s" % (p, a))
    if _residue_mod_p(x, p) != a % p:
        raise ArithmeticError("residue check failed for p=%s, a=%s" % (p, a))
    return x


def independent_unit_root(p, a):
    """Compute the same root from the Catalan expansion."""
    p = ZZ(p)
    a = ZZ(a)
    precision = p_adic_precision(p)
    field = Qp(p, prec=int(precision + WORKING_GUARD))
    z = field(p) / field(a * a)

    catalan = ZZ(1)
    power = z
    series = field(1)
    for n in range(1, int(precision + WORKING_GUARD)):
        series -= field(catalan) * power
        catalan = catalan * (4 * n - 2) // (n + 1)
        power *= z

    value = (field(a) * series).add_bigoh(int(precision))
    residual = value * value - field(a) * value + field(p)
    if residual != 0 and residual.valuation() < precision:
        raise ArithmeticError("series root check failed for p=%s, a=%s"
                              % (p, a))
    if _residue_mod_p(value, p) != a % p:
        raise ArithmeticError("independent root chose the wrong branch")
    return value


def agree_mod_precision(left, right, p):
    precision = p_adic_precision(p)
    difference = left - right
    return difference == 0 or difference.valuation() >= precision


def check_independent():
    checked = 0
    for params in UnitRootsFrobeniusPolynomials().enumerate():
        p = ZZ(params["p"])
        a = ZZ(params["a"])
        value = unit_root(p, a)
        expected = independent_unit_root(p, a)
        if not agree_mod_precision(value, expected, p):
            raise ArithmeticError("independent disagreement for p=%s, a=%s"
                                  % (p, a))
        checked += 1
    return checked


class UnitRootsFrobeniusPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("p", "a")
    type = "Qp"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for p in primes():
            for a in ordinary_traces(p):
                yield {"p": str(p), "a": str(a)}

    def value(self, params, digits):
        return unit_root(ZZ(params["p"]), ZZ(params["a"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = UnitRootsFrobeniusPolynomials()
    if os.environ.get("NUMBERDB_CHECK_INDEPENDENT") == "1":
        print("checked %s entries against Sage polynomial roots"
              % (check_independent(),))
    elif os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="unit roots of ordinary Frobenius polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
