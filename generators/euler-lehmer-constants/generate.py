"""Euler-Lehmer constants -- numberdb.org/T231

For each integer q with 1 <= q <= 30 and each residue class 0 <= a < q, this
stores the Euler-Lehmer constant gamma(a, q), defined by

    gamma(a, q) = lim_x (sum_{0 < n <= x, n = a mod q} 1/n - log(x)/q).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls using arb's digamma function:

    gamma(0, q) = (gamma - log q) / q
    gamma(a, q) = -(psi(a/q) + log q) / q, 1 <= a < q.

The identity check mode compares every row with an independent root-of-unity
logarithm formula and checks the sum and subdivision identities.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import gcd
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


MAX_Q = 30
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _complex_field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _finite(value, label):
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    return value


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s" % (label,))
    return value.real()


def _validate_parameters(a, q):
    a = ZZ(a)
    q = ZZ(q)
    if q < 1:
        raise ValueError("expected q >= 1")
    if a < 0 or a >= q:
        raise ValueError("expected 0 <= a < q")
    return a, q


def euler_lehmer(a, q, digits):
    a, q = _validate_parameters(a, q)
    field = _field(digits)
    log_q = field(q).log()
    if a == 0:
        return _finite((field.euler_constant() - log_q) / field(q),
                       "gamma(0,%s)" % (q,))
    x = QQ(a) / QQ(q)
    value = -(field(x).psi() + log_q) / field(q)
    return _finite(value, "gamma(%s,%s)" % (a, q))


def euler_lehmer_by_roots(a, q, digits):
    """Independent check from Wikipedia's finite root-of-unity formula."""
    a, q = _validate_parameters(a, q)
    field = _complex_field(digits)
    real_field = _field(digits)
    zeta = (2 * field.pi() * field(0, 1) / field(q)).exp()
    total = field(0)
    for j in range(1, int(q)):
        total += zeta ** (-int(a) * j) * (1 - zeta ** j).log()
    return _real((field(real_field.euler_constant()) - total) / field(q),
                 "root formula for gamma(%s,%s)" % (a, q))


def _comment(a, q):
    if q == 1 and a == 0:
        return "Euler's constant, the Stieltjes constant $\\gamma_0$."
    if q == 2 and a == 1:
        return "$(\\gamma+\\log2)/2$."
    if q == 4 and a == 1:
        return "$(\\gamma+\\pi/2+\\log2)/4$."
    return ""


class EulerLehmerConstants(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T231")
    parameters = ("q", "a")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, maximum=MAX_Q):
        for q in range(1, maximum + 1):
            for a in range(q):
                yield {"q": q, "a": a}

    def value(self, params, digits):
        q = ZZ(params["q"])
        a = ZZ(params["a"])
        value = euler_lehmer(a, q, digits)
        comment = _comment(int(a), int(q))
        if comment:
            return {"number": value, "comment": comment}
        return value


def _assert_contains_zero(value, label):
    if not value.is_finite():
        raise AssertionError("%s produced a non-finite ball" % (label,))
    if not value.contains_zero():
        raise AssertionError("%s differs by %s" % (label, value))


def check_identities(maximum=MAX_Q, digits=100):
    field = _field(digits)
    values = {}
    for q in range(1, maximum + 1):
        for a in range(q):
            values[(q, a)] = euler_lehmer(a, q, digits)

    for (q, a), value in values.items():
        _assert_contains_zero(
            value - euler_lehmer_by_roots(a, q, digits),
            "root-of-unity formula at q=%s, a=%s" % (q, a),
        )

    for q in range(1, maximum + 1):
        total = sum(values[(q, a)] for a in range(q))
        _assert_contains_zero(
            total - field.euler_constant(),
            "sum identity at q=%s" % (q,),
        )

    for q in range(1, maximum + 1):
        for a in range(q):
            d = ZZ(q) if a == 0 else gcd(ZZ(a), ZZ(q))
            left = field(q) * values[(q, a)]
            right = field(q // d) * values[(int(q // d), int(a // d))]
            right -= field(d).log()
            _assert_contains_zero(
                left - right,
                "gcd identity at q=%s, a=%s" % (q, a),
            )

    _assert_contains_zero(values[(1, 0)] - field.euler_constant(),
                          "gamma(0,1)")
    _assert_contains_zero(
        values[(2, 1)] - (field.euler_constant() + field(2).log()) / 2,
        "gamma(1,2)",
    )
    _assert_contains_zero(
        values[(4, 1)] - (
            field.euler_constant() + field.pi() / 2 + field(2).log()) / 4,
        "gamma(1,4)",
    )
    return len(values)


if __name__ == "__main__":
    _key_from_stdin()
    generator = EulerLehmerConstants()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        count = check_identities()
        print("checked identities on %d entries" % count)
    elif os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Euler-Lehmer constants for q <= 30"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
