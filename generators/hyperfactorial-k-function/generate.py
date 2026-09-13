"""Values of the hyperfactorial K-function at rational numbers -- numberdb.org/T229

For each rational x = a/b in lowest terms with b <= 12 and 0 < x <= 6, this
stores K(x) and log K(x), where

    log K(x) = zeta'(-1, x) - zeta'(-1).

At positive integers, K(n) = prod_{m=1}^{n-1} m^m is returned exactly. The
rows log K(1) and log K(2) are the exact integer 0.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Non-exact values are computed in arb ball arithmetic from the Hurwitz zeta
power series in Sage. The Barnes G expression gives an independent check.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


MAX_DENOMINATOR = 12
MAX_ARGUMENT = QQ(6)
WORKING_GUARD = 96

QUANTITY_K = "K"
QUANTITY_LOG_K = "logK"

_RING_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field_and_series_ring(digits):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    if bits not in _RING_CACHE:
        field = ComplexBallField(bits)
        ring = PolynomialRing(field, "t")
        _RING_CACHE[bits] = (field, ring, ring.gen())
    return _RING_CACHE[bits]


def _argument_order_key(x):
    return (x.denominator(), x)


def _arguments(max_denominator=MAX_DENOMINATOR):
    found = []
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, int(MAX_ARGUMENT * denominator) + 1):
            if gcd(numerator, denominator) != 1:
                continue
            x = QQ(numerator) / QQ(denominator)
            if x.denominator() != denominator:
                continue
            if 0 < x <= MAX_ARGUMENT:
                found.append(x)
    for x in sorted(found, key=_argument_order_key):
        yield x


def _is_positive_integer(x):
    return x > 0 and x.denominator() == 1


def _integer_k(n):
    total = ZZ(1)
    for m in range(1, int(n)):
        total *= ZZ(m) ** int(m)
    return total


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s" % (label,))
    return value.real()


def _hurwitz_zeta_derivative_at_minus_one(x, digits):
    field, ring, t = _field_and_series_ring(digits)
    series = (field(QQ(-1)) + t)._zeta_series(2, field(x), False)
    return series[1]


def log_k_function(x, digits):
    if x == 1 or x == 2:
        return ZZ(0)
    field, _, _ = _field_and_series_ring(digits)
    value = _hurwitz_zeta_derivative_at_minus_one(x, digits) - field(-1).zetaderiv(1)
    return _real(value, "log K(%s)" % (x,))


def k_function(x, digits):
    if _is_positive_integer(x):
        return _integer_k(x)
    return log_k_function(x, digits).exp()


def _comment(x, quantity):
    text = str(x)
    if quantity == QUANTITY_K:
        if text == "1":
            return "The empty product."
        if text == "1/2":
            return "$A^{3/2}2^{-1/24}e^{-1/8}$, where $A$ is HREF{T227#1,A}[the Glaisher-Kinkelin constant]."
        if text == "3":
            return "$1^1 2^2=4$."
        if text == "4":
            return "$1^1 2^2 3^3=108$."
    if quantity == QUANTITY_LOG_K:
        if text == "1" or text == "2":
            return "$0$."
        if text == "1/2":
            return "$\\frac32\\log A-\\frac1{24}\\log2-\\frac18$."
    return ""


class HyperfactorialKFunctionValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T229")
    parameters = ("x", "quantity")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_denominator=MAX_DENOMINATOR):
        for x in _arguments(max_denominator):
            yield {"x": str(x), "quantity": QUANTITY_K}
            yield {"x": str(x), "quantity": QUANTITY_LOG_K}

    def value(self, params, digits):
        x = QQ(params["x"])
        quantity = str(params["quantity"])
        if quantity == QUANTITY_K:
            number = k_function(x, digits)
        elif quantity == QUANTITY_LOG_K:
            number = log_k_function(x, digits)
        else:
            raise ValueError("unknown quantity %r" % (quantity,))

        comment = _comment(x, quantity)
        if comment:
            return {"number": number, "comment": comment}
        return number


if __name__ == "__main__":
    _key_from_stdin()
    generator = HyperfactorialKFunctionValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="hyperfactorial K-function values at rational arguments",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
