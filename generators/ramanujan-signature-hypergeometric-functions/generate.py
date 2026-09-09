"""Ramanujan signature hypergeometric functions -- numberdb.org/T178

    F_r(x) = 2F1(1/r, 1 - 1/r; 1; x),

for r in {2, 3, 4, 6} and rational 0 < x < 1, with x written in lowest terms
and denominator at most 20.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls. The Gauss series is used for x <= 1/2; the
logarithmic connection series at x = 1 is used for x > 1/2.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


SIGNATURES = (2, 3, 4, 6)
MAX_DENOMINATOR = 20
TAIL_GUARD_DIGITS = 30

# Bits of working precision beyond what the written digits need.
#
# Measured over all 508 entries: at this guard the widest result still has
# radius less than 6e-130 when the table asks for 100 digits.
WORKING_GUARD = 128


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _target(digits):
    return QQ(1) / (QQ(10) ** (digits + TAIL_GUARD_DIGITS))


def _signature_parameters(r):
    a = QQ(1) / QQ(r)
    return a, QQ(1) - a


def _rationals(max_denominator=MAX_DENOMINATOR):
    for denominator in range(2, max_denominator + 1):
        for numerator in range(1, denominator):
            if gcd(numerator, denominator) == 1:
                yield QQ(numerator) / QQ(denominator)


def _add_positive_error(value, error):
    if error <= 0:
        raise ArithmeticError("tail bound must be positive")
    return value.add_error(error)


def _direct_series(field, a, b, xq, digits):
    """Gauss series with c_k <= 1, so the tail is at most x^N/(1-x)."""
    x = field(xq)
    total = field(0)
    coeff = field(1)
    power = field(1)
    k = 0
    while True:
        total += coeff * power
        k += 1
        power *= x
        coeff *= field(a + k - 1) * field(b + k - 1) / field(k * k)
        tail = (xq ** k) / (QQ(1) - xq)
        if tail < _target(digits):
            return _add_positive_error(total, field(tail))


def _connection_prefactor(field, a):
    return (field.pi() * field(a)).sin() / field.pi()


def _connection_tail_bound(field, prefactor, bracket0, yq, k):
    bound = prefactor.upper() * bracket0.upper() * (yq ** k) / (QQ(1) - yq)
    return field(bound)


def _connection_series(field, a, b, xq, digits):
    """DLMF 15.8.10 with m = 0, with a monotone digamma-difference tail."""
    yq = QQ(1) - xq
    y = field(yq)
    prefactor = _connection_prefactor(field, a)
    minus_log_y = -y.log()
    bracket0 = field(2) * field(1).psi() - field(a).psi() - field(b).psi()
    bracket0 += minus_log_y
    if not bracket0 > 0:
        raise ArithmeticError("connection-series tail bound is not positive")

    total = field(0)
    coeff = field(1)
    power = field(1)
    k = 0
    while True:
        bracket = field(2) * field(k + 1).psi()
        bracket -= field(a + k).psi() + field(b + k).psi()
        bracket += minus_log_y
        total += coeff * bracket * power
        k += 1
        tail = _connection_tail_bound(field, prefactor, bracket0, yq, k)
        if tail < field(_target(digits)):
            return _add_positive_error(prefactor * total, tail)
        power *= y
        coeff *= field(a + k - 1) * field(b + k - 1) / field(k * k)


def _value_ball(r, x_text, digits):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    xq = QQ(x_text)
    a, b = _signature_parameters(r)
    if xq <= QQ(1) / QQ(2):
        value = _direct_series(field, a, b, xq, digits)
    else:
        value = _connection_series(field, a, b, xq, digits)
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball")
    return value


def _comment(r, x):
    if x == "1/2":
        return "A Gauss second-summation value, equal to $2/B((r+1)/(2r),(2r-1)/(2r))$."
    if r == 2:
        return (
            "It equals $2K(x)/\\pi$, with "
            "HREF{Complete_elliptic_integral_of_the_first_kind_K}[$K$] the "
            "complete elliptic integral of the first kind."
        )
    if r == 3 and x in ("1/4", "9/10"):
        return "$1/\\mathrm{AGM}_3(1,(1-x)^{1/3})$."
    return ""


class RamanujanSignatureHypergeometricFunctions(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T178")
    parameters = ("r", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, signatures=SIGNATURES, denominator=MAX_DENOMINATOR):
        for x in _rationals(denominator):
            for r in signatures:
                yield {"r": str(r), "x": str(x)}

    def value(self, params, digits):
        r = int(params["r"])
        x_text = str(params["x"])
        value = _value_ball(r, x_text, digits)
        comment = _comment(r, x_text)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = RamanujanSignatureHypergeometricFunctions()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="Ramanujan signature hypergeometric values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
